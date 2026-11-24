"""Synchronized lyrics provider using LRCLIB API with zero external dependencies."""

import json
import logging
import re
import threading
import urllib.parse
import urllib.request
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Matches [mm:ss.xx] or [mm:ss.xxx] followed by lyric text
LRC_REGEX = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\](.*)")


class LyricsLine:
    """Represents a single timed line of synchronized lyrics."""

    def __init__(self, time_ms: int, text: str) -> None:
        self.time_ms = time_ms
        self.text = text.strip()

    def __repr__(self) -> str:
        return f"LyricsLine({self.time_ms}ms, '{self.text}')"


class LyricsProvider:
    """Asynchronous, thread-safe synchronized lyrics provider backed by LRCLIB."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cached_track_key: Optional[str] = None
        self._cached_lines: List[LyricsLine] = []
        self._plain_lyrics: Optional[str] = None
        self._is_fetching = False

    def fetch_lyrics_async(
        self,
        title: str,
        artist: str,
        duration_ms: int = 0,
    ) -> None:
        """Fetch synchronized lyrics in a background thread."""
        if not title or not artist or artist.lower() == "no media playing":
            with self._lock:
                self._cached_lines = []
                self._cached_track_key = None
            return

        track_key = f"{artist.strip().lower()} - {title.strip().lower()}"
        with self._lock:
            if self._cached_track_key == track_key or self._is_fetching:
                return
            self._is_fetching = True

        threading.Thread(
            target=self._worker_fetch,
            args=(track_key, title, artist, duration_ms),
            daemon=True,
            name="LyricsFetchWorker",
        ).start()

    def _worker_fetch(
        self,
        track_key: str,
        title: str,
        artist: str,
        duration_ms: int,
    ) -> None:
        """Background worker issuing HTTP request to LRCLIB API."""
        try:
            params = {
                "track_name": title,
                "artist_name": artist,
            }
            if duration_ms > 0:
                params["duration"] = str(duration_ms // 1000)

            url = f"https://lrclib.net/api/get?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MediaDock/1.0 (Desktop Media Controller)"},
            )

            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    synced = data.get("syncedLyrics")
                    plain = data.get("plainLyrics")
                    lines = self._parse_lrc(synced) if synced else []

                    with self._lock:
                        self._cached_track_key = track_key
                        self._cached_lines = lines
                        self._plain_lyrics = plain
                    return
        except Exception as e:
            logger.debug("Lyrics fetch skipped/failed for %s: %s", track_key, e)
        finally:
            with self._lock:
                self._is_fetching = False

    @staticmethod
    def _parse_lrc(lrc_text: str) -> List[LyricsLine]:
        """Parse raw LRC text into sorted list of LyricsLine objects."""
        lines: List[LyricsLine] = []
        if not lrc_text:
            return lines

        for raw_line in lrc_text.splitlines():
            raw_line = raw_line.strip()
            match = LRC_REGEX.match(raw_line)
            if not match:
                continue

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
            text = match.group(4).strip()
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
