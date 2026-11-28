"""Unit tests for ArtworkResolver (online album art fallback)."""

import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication

from src.media.artwork_resolver import ArtworkResolver

app = QApplication.instance() or QApplication([])


class TestArtworkResolver(unittest.TestCase):
    """Test suite for ArtworkResolver caching and network fallback logic."""

    def setUp(self) -> None:
        self.resolver = ArtworkResolver()

    def test_cache_and_get_artwork(self) -> None:
        """Verify caching artwork stores and retrieves bytes correctly."""
        dummy_bytes = b"fake_png_data"
        self.resolver.cache_artwork("Borderline", "Tame Impala", dummy_bytes)
        retrieved = self.resolver.get_cached_artwork("Borderline", "Tame Impala")
        self.assertEqual(retrieved, dummy_bytes)

        # Case-insensitivity check
        retrieved_lower = self.resolver.get_cached_artwork("borderline", "tame impala")
        self.assertEqual(retrieved_lower, dummy_bytes)

    def test_resolve_empty_or_no_media_does_nothing(self) -> None:
        """Verify empty or dummy tracks don't trigger network calls."""
        received = []
        self.resolver.artwork_resolved.connect(lambda t, a, b: received.append((t, a, b)))
        self.resolver.resolve_artwork_async("", "")
        self.resolver.resolve_artwork_async("No Media Playing", "")
        self.assertEqual(len(received), 0)

    @patch("urllib.request.urlopen")
    def test_fetch_itunes_success(self, mock_urlopen: MagicMock) -> None:
        """Verify iTunes API response parsing and image download."""
        search_json = b'{"resultCount": 1, "results": [{"artworkUrl100": "http://example.com/100x100bb.jpg"}]}'
        image_bytes = b"\x89PNG\r\n\x1a\nfakeimage"

        mock_search_resp = MagicMock()
        mock_search_resp.read.return_value = search_json
        mock_search_resp.__enter__.return_value = mock_search_resp

        mock_img_resp = MagicMock()
        mock_img_resp.read.return_value = image_bytes
        mock_img_resp.__enter__.return_value = mock_img_resp

        mock_urlopen.side_effect = [mock_search_resp, mock_img_resp]

        result = ArtworkResolver._fetch_itunes("Borderline", "Tame Impala")
        self.assertEqual(result, image_bytes)

    @patch("urllib.request.urlopen")
    def test_fetch_itunes_no_results(self, mock_urlopen: MagicMock) -> None:
        """Verify iTunes returns None when results are empty."""
        empty_json = b'{"resultCount": 0, "results": []}'

        mock_resp = MagicMock()
        mock_resp.read.return_value = empty_json
        mock_resp.__enter__.return_value = mock_resp

        mock_urlopen.return_value = mock_resp

        result = ArtworkResolver._fetch_itunes("NonexistentSong12345", "UnknownArtist99999")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
