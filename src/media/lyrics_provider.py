"""Synchronized lyrics provider using LRCLIB API with zero external dependencies."""

import json
import logging
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Matches [mm:ss.xx] or [mm:ss.xxx] or repeated tags e.g. [00:12.34][00:24.56]
TAG_REGEX = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")

# Noise patterns to strip from track titles for reliable LRCLIB matching
TITLE_NOISE_PATTERNS = [
    re.compile(
        r"\s*[\(\[\{](?:official\s*(?:music\s*)?video|official\s*audio|music\s*video|lyric\s*video|audio|lyrics|visualizer|4k|hd|remaster(?:ed)?(?:\s*\d+)?|live(?:\s+at[^\)\]\}]*)?)[\)\]\}]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\s*-\s*(?:(?:\d{4}\s+)?remaster(?:ed)?(?:\s*\d{4})?|live(?:\s+at.*)?|radio\s*edit|club\s*mix|single\s*version|original\s*mix|official\s*video|bonus\s*track).*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\s*[\(\[\{](?:feat\.|ft\.|featuring)\s+[^\)\]\}]+[\)\]\}]",
        re.IGNORECASE,
    ),
]

GENERIC_ARTIST_NAMES = {
    "youtube",
    "google chrome",
    "chrome",
    "msedge",
    "microsoft edge",
    "firefox",
    "brave",
    "opera",
    "unknown artist",
    "unknown",
    "no media playing",
    "",
}


def sanitize_metadata(title: str, artist: str) -> Tuple[str, str]:
    """Clean common metadata noise (remaster tags, video labels, feat tags, browser/YouTube prefixes).
    
    Returns a cleaned (title, artist) tuple optimized for database matching.
    """
    if not title:
        return ("", (artist or "").strip())

    clean_title = title.strip()
    clean_artist = (artist or "").strip()

    # Browser & YouTube sessions often set artist to browser/channel name and title to "Artist - Title"
    if clean_artist.lower() in GENERIC_ARTIST_NAMES and " - " in clean_title:
        parts = clean_title.split(" - ", 1)
        if parts[0].strip() and parts[1].strip():
            clean_artist = parts[0].strip()
            clean_title = parts[1].strip()

    # Strip noise patterns from title
    for pat in TITLE_NOISE_PATTERNS:
        clean_title = pat.sub("", clean_title)

    clean_title = clean_title.strip(" -–—\"'[]()")
    clean_artist = clean_artist.strip(" -–—\"'[]()")

    return (clean_title or title.strip(), clean_artist or (artist or "").strip())


class LyricsLine:
    """Represents a single timed line of synchronized lyrics."""

    def __init__(self, time_ms: int, text: str) -> None:
        self.time_ms = time_ms
        self.text = text.strip()

    def __repr__(self) -> str:
        return f"LyricsLine({self.time_ms}ms, '{self.text}')"


class LyricsProvider:
    """Asynchronous, thread-safe synchronized lyrics provider backed by LRCLIB with search fallback."""

    def __init__(
        self,
        on_lyrics_loaded: Optional[Callable[[str, bool], None]] = None,
    ) -> None:
        self._lock = threading.Lock()
        self._cached_track_key: Optional[str] = None
        self._cached_lines: List[LyricsLine] = []
        self._plain_lyrics: Optional[str] = None
        self._current_fetch_id: int = 0
        self._on_lyrics_loaded: Optional[Callable[[str, bool], None]] = on_lyrics_loaded

    def set_lyrics_loaded_callback(
        self,
        callback: Optional[Callable[[str, bool], None]],
    ) -> None:
        """Register or update completion callback (called with track_key, has_synced_lyrics)."""
        with self._lock:
            self._on_lyrics_loaded = callback

    def has_synced_lyrics(self) -> bool:
        """Return True if the currently cached track has one or more timestamped lyrics lines."""
        with self._lock:
            return len(self._cached_lines) > 0

    def get_plain_lyrics(self) -> Optional[str]:
        """Return unsynchronized plain text lyrics if available."""
        with self._lock:
            return self._plain_lyrics

    def fetch_lyrics_async(
        self,
        title: str,
        artist: str,
        duration_ms: int = 0,
    ) -> None:
        """Fetch synchronized lyrics in a background thread without dropping rapid track changes."""
        if not title or not artist or artist.lower() == "no media playing":
            with self._lock:
                self._cached_lines = []
                self._plain_lyrics = None
                self._cached_track_key = None
            return

        track_key = f"{artist.strip().lower()} - {title.strip().lower()}"
        with self._lock:
            # If already cached for this exact track, invoke callback immediately
            if self._cached_track_key == track_key:
                has_synced = len(self._cached_lines) > 0
                cb = self._on_lyrics_loaded
                if cb:
                    try:
                        cb(track_key, has_synced)
                    except Exception as e:
                        logger.debug("Error invoking cached lyrics callback: %s", e)
                return

            # Supersede previous fetch requests without blocking new ones
            self._current_fetch_id += 1
            fetch_id = self._current_fetch_id

        threading.Thread(
            target=self._worker_fetch,
            args=(fetch_id, track_key, title, artist, duration_ms),
            daemon=True,
            name="LyricsFetchWorker",
        ).start()

    def _worker_fetch(
        self,
        fetch_id: int,
        track_key: str,
        title: str,
        artist: str,
        duration_ms: int,
    ) -> None:
        """Multi-tier worker: exact /api/get -> sanitized /api/get -> fallback /api/search."""
        clean_title, clean_artist = sanitize_metadata(title, artist)
        duration_sec = duration_ms // 1000 if duration_ms > 0 else 0

        synced_text: Optional[str] = None
        plain_text: Optional[str] = None

        # Check if already superseded before doing network I/O
        with self._lock:
            if self._current_fetch_id != fetch_id:
                return

        # --- Tier 1: Exact /api/get with raw metadata ---
        synced_text, plain_text = self._try_api_get(title, artist, duration_sec)

        # --- Tier 2: Sanitized /api/get if raw failed or had no synced lyrics ---
        if not synced_text and (clean_title != title or clean_artist != artist):
            with self._lock:
                if self._current_fetch_id != fetch_id:
                    return
            s2, p2 = self._try_api_get(clean_title, clean_artist, duration_sec)
            if s2:
                synced_text = s2
                plain_text = p2 or plain_text
            elif p2 and not plain_text:
                plain_text = p2

        # --- Tier 3: /api/search fallback if still no synced lyrics ---
        if not synced_text:
            with self._lock:
                if self._current_fetch_id != fetch_id:
                    return
            s3, p3 = self._try_api_search(clean_title, clean_artist, duration_sec)
            if s3:
                synced_text = s3
                plain_text = p3 or plain_text
            elif p3 and not plain_text:
                plain_text = p3

        # Parse synchronized lines
        lines = self._parse_lrc(synced_text) if synced_text else []

        # Commit result under lock if not superseded
        callback_to_call: Optional[Callable[[str, bool], None]] = None
        has_synced: bool = False

        with self._lock:
            if self._current_fetch_id != fetch_id:
                logger.debug("Lyrics fetch id %d superseded by %d", fetch_id, self._current_fetch_id)
                return

            self._cached_track_key = track_key
            self._cached_lines = lines
            self._plain_lyrics = plain_text
            callback_to_call = self._on_lyrics_loaded
            has_synced = len(lines) > 0

        if callback_to_call:
            try:
                callback_to_call(track_key, has_synced)
            except Exception as e:
                logger.debug("Error in on_lyrics_loaded callback for %s: %s", track_key, e)

    def _try_api_get(
        self,
        track_name: str,
        artist_name: str,
        duration_sec: int = 0,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Call LRCLIB /api/get endpoint."""
        if not track_name or not artist_name:
            return (None, None)

        params = {
            "track_name": track_name,
            "artist_name": artist_name,
        }
        # Only pass duration if > 0
        if duration_sec > 0:
            params["duration"] = str(duration_sec)

        url = f"https://lrclib.net/api/get?{urllib.parse.urlencode(params)}"
        data = self._http_get_json(url)

        if isinstance(data, dict):
            synced = data.get("syncedLyrics")
            plain = data.get("plainLyrics")
            if synced or plain:
                return (synced, plain)

        # If /api/get with duration failed (due to slight duration variance), retry without duration
        if duration_sec > 0:
            params.pop("duration", None)
            url_no_dur = f"https://lrclib.net/api/get?{urllib.parse.urlencode(params)}"
            data_no_dur = self._http_get_json(url_no_dur)
            if isinstance(data_no_dur, dict):
                synced = data_no_dur.get("syncedLyrics")
                plain = data_no_dur.get("plainLyrics")
                if synced or plain:
                    return (synced, plain)

        return (None, None)

    def _try_api_search(
        self,
        clean_title: str,
        clean_artist: str,
        duration_sec: int = 0,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Call LRCLIB /api/search endpoint and pick best matching synced lyrics."""
        query_parts = [p for p in (clean_artist, clean_title) if p]
        if not query_parts:
            return (None, None)

        query = " ".join(query_parts)
        url = f"https://lrclib.net/api/search?q={urllib.parse.quote(query)}"
        data = self._http_get_json(url)

        if not isinstance(data, list) or not data:
            return (None, None)

        # Candidates with syncedLyrics
        synced_candidates = [item for item in data if isinstance(item, dict) and item.get("syncedLyrics")]

        if synced_candidates:
            # If duration is known, prefer candidate with closest duration within 15 seconds
            if duration_sec > 0:
                best_item = min(
                    synced_candidates,
                    key=lambda it: abs(int(it.get("duration") or 0) - duration_sec),
                )
                return (best_item.get("syncedLyrics"), best_item.get("plainLyrics"))
            # Otherwise return first candidate with syncedLyrics
            return (synced_candidates[0].get("syncedLyrics"), synced_candidates[0].get("plainLyrics"))

        # Fallback to plain lyrics from top item if no synced lyrics found
        first_plain = next((it.get("plainLyrics") for it in data if isinstance(it, dict) and it.get("plainLyrics")), None)
        return (None, first_plain)

    @staticmethod
    def _http_get_json(url: str, timeout: float = 3.5) -> Optional[dict | list]:
        """Execute HTTP GET request and return parsed JSON or None on failure."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MediaDock/1.0 (Desktop Media Controller; LRCLIB Integration)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    raw_bytes = resp.read()
                    return json.loads(raw_bytes.decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as he:
            logger.debug("LRCLIB HTTP %d for %s", he.code, url)
        except Exception as e:
            logger.debug("LRCLIB request error for %s: %s", url, e)
        return None

    @staticmethod
    def _parse_lrc(lrc_text: str) -> List[LyricsLine]:
        """Parse raw LRC text into sorted list of LyricsLine objects."""
        lines: List[LyricsLine] = []
        if not lrc_text:
            return lines

        for raw_line in lrc_text.splitlines():
            raw_line = raw_line.strip()
            matches = list(TAG_REGEX.finditer(raw_line))
            if not matches:
                continue

            # Strip all matched timestamp tags to get text
            text = TAG_REGEX.sub("", raw_line).strip()

            for match in matches:
                mins = int(match.group(1))
                secs = int(match.group(2))
                millis_str = match.group(3) or "0"
                if len(millis_str) == 2:
                    millis = int(millis_str) * 10
                elif len(millis_str) == 1:
                    millis = int(millis_str) * 100
                else:
                    millis = int(millis_str[:3])

                total_ms = (mins * 60 + secs) * 1000 + millis
                lines.append(LyricsLine(total_ms, text))

        lines.sort(key=lambda l: l.time_ms)
        return lines

    def get_current_lyric(self, position_ms: int) -> Optional[str]:
        """Return the active synchronized lyric line for the given playback position in milliseconds."""
        with self._lock:
            if not self._cached_lines:
                return None

            active_text = None
            for line in self._cached_lines:
                if line.time_ms <= position_ms:
                    active_text = line.text
                else:
                    break

            return active_text
