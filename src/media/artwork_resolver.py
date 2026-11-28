"""Online album artwork resolver using iTunes Search API fallback when GSMTC provides no thumbnail."""

import json
import logging
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from src.media.lyrics_provider import sanitize_metadata

logger = logging.getLogger(__name__)


class ArtworkResolver(QObject):
    """Fetches high-resolution album cover art in background thread when OS SMTC provides None."""

    artwork_resolved = Signal(str, str, bytes)  # (title, artist, image_bytes)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._cache: Dict[Tuple[str, str], Optional[bytes]] = {}
        self._pending_threads: Dict[Tuple[str, str], threading.Thread] = {}
        self._lock = threading.Lock()

    def get_cached_artwork(self, title: str, artist: str) -> Optional[bytes]:
        """Return cached artwork bytes if previously fetched."""
        key = (title.strip().lower(), artist.strip().lower())
        with self._lock:
            return self._cache.get(key)

    def cache_artwork(self, title: str, artist: str, art_bytes: bytes) -> None:
        """Cache known artwork bytes (e.g. from WinRT SMTC)."""
        if not title or not art_bytes:
            return
        key = (title.strip().lower(), artist.strip().lower())
        with self._lock:
            self._cache[key] = art_bytes

    def resolve_artwork_async(self, title: str, artist: str) -> None:
        """Launch background worker to fetch artwork from iTunes Search API if not already cached."""
        clean_title, clean_artist = sanitize_metadata(title, artist)
        if not clean_title or clean_title == "No Media Playing":
            return

        key = (title.strip().lower(), artist.strip().lower())
        with self._lock:
            if key in self._cache:
                cached = self._cache[key]
                if cached:
                    self.artwork_resolved.emit(title, artist, cached)
                return
            if key in self._pending_threads and self._pending_threads[key].is_alive():
                return

            worker = threading.Thread(
                target=self._worker_fetch,
                args=(title, artist, clean_title, clean_artist),
                daemon=True,
                name=f"ArtworkWorker-{clean_title[:15]}",
            )
            self._pending_threads[key] = worker
            worker.start()

    def _worker_fetch(self, orig_title: str, orig_artist: str, title: str, artist: str) -> None:
        """Background thread worker fetching and downscaling/caching artwork."""
        art_bytes = self._fetch_itunes(title, artist)
        key = (orig_title.strip().lower(), orig_artist.strip().lower())
        with self._lock:
            self._cache[key] = art_bytes
            self._pending_threads.pop(key, None)

        if art_bytes:
            logger.info("Successfully fetched online album art for %s - %s (%d bytes)", artist, title, len(art_bytes))
            self.artwork_resolved.emit(orig_title, orig_artist, art_bytes)

    @staticmethod
    def _fetch_itunes(title: str, artist: str) -> Optional[bytes]:
        """Query iTunes Search API and download high-resolution cover."""
        query_str = f"{artist} {title}".strip() if artist else title
        encoded_query = urllib.parse.quote(query_str)
        url = f"https://itunes.apple.com/search?term={encoded_query}&entity=song&limit=1"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MediaDock/1.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = data.get("results", [])
            if not results:
                # Retry with just the title if artist was composite or unusual
                if artist:
                    url_retry = f"https://itunes.apple.com/search?term={urllib.parse.quote(title)}&entity=song&limit=1"
                    req_retry = urllib.request.Request(
                        url_retry,
                        headers={"User-Agent": "MediaDock/1.0 (Windows NT 10.0; Win64; x64)"},
                    )
                    with urllib.request.urlopen(req_retry, timeout=4) as retry_resp:
                        data = json.loads(retry_resp.read().decode("utf-8"))
                        results = data.get("results", [])

            if not results:
                return None

            raw_url = results[0].get("artworkUrl100", "")
            if not raw_url:
                return None

            # Upscale artwork to 512x512 for sharp display on 92x92 retina tiles
            hi_res_url = raw_url.replace("100x100bb", "512x512bb")
            img_req = urllib.request.Request(
                hi_res_url,
                headers={"User-Agent": "MediaDock/1.0"},
            )
            with urllib.request.urlopen(img_req, timeout=5) as img_resp:
                return img_resp.read()
        except Exception as e:
            logger.debug("Could not resolve online artwork for '%s': %s", query_str, e)
            return None
