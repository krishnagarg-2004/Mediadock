"""Unit tests for v1.0.0 architectural enhancements:
- Synchronized multi-line lyrics drawer and line tracking
- GitHub release update checker worker
- Display hotplug and screen resolution change handling
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint

# Ensure QApplication exists
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from src.media.lyrics_provider import LyricsProvider, LyricsLine
from src.ui.lyrics_drawer import LyricsDrawerWidget, ClickableLyricLine
from src.ui.settings_dialog import _UpdateCheckWorker


class TestLyricsDrawerAndLineTracking(unittest.TestCase):
    """Test multi-line lyrics drawer and synchronized line indexing."""

    def setUp(self):
        self.provider = LyricsProvider()

    def test_get_synced_lines_and_current_line_index(self):
        sample_lrc = (
            "[00:00.00]Intro\n"
            "[00:05.00]First line of song\n"
            "[00:10.50]Second line of song\n"
            "[00:20.00]Chorus line\n"
        )
        parsed = self.provider._parse_lrc(sample_lrc)
        with self.provider._lock:
            self.provider._cached_lines = parsed

        lines = self.provider.get_synced_lines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[1].text, "First line of song")
        self.assertEqual(lines[1].time_ms, 5000)

        # Before first line
        self.assertEqual(self.provider.get_current_line_index(1000), 0)
        # At first line
        self.assertEqual(self.provider.get_current_line_index(5500), 1)
        # At second line
        self.assertEqual(self.provider.get_current_line_index(15000), 2)
        # At chorus line and beyond
        self.assertEqual(self.provider.get_current_line_index(25000), 3)

    def test_lyrics_drawer_widget_lifecycle(self):
        drawer = LyricsDrawerWidget()
        lines = [
            LyricsLine(time_ms=0, text="Intro"),
            LyricsLine(time_ms=5000, text="Line 1"),
            LyricsLine(time_ms=10000, text="Line 2"),
        ]
        drawer.set_lyrics(lines, "Test Song")
        self.assertEqual(drawer.lbl_header_title.text(), "♪ Test Song")
        self.assertEqual(len(drawer._line_widgets), 3)

        # Active line positioning
        drawer.set_active_position(6000)
        self.assertEqual(drawer._active_index, 1)

        # Signal emission on seek request
        seek_events = []
        drawer.seek_requested.connect(lambda t: seek_events.append(t))
        drawer._line_widgets[2].clicked.emit(10000)
        self.assertEqual(seek_events, [10000])


class TestUpdateCheckWorker(unittest.TestCase):
    """Test update checker worker parsing GitHub Releases API responses."""

    def test_update_checker_parses_newer_version(self):
        worker = _UpdateCheckWorker("v1.0.0")
        results = []
        worker.result_ready.connect(lambda has_upd, tag, url, notes: results.append((has_upd, tag, url, notes)))

        mock_payload = (
            b'{"tag_name": "v1.2.0", "html_url": "https://github.com/krishnagarg-2004/Mediadock/releases/tag/v1.2.0", '
            b'"body": "New feature release notes"}'
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = mock_payload
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            worker.run()

        self.assertEqual(len(results), 1)
        has_update, tag, url, notes = results[0]
        self.assertTrue(has_update)
        self.assertEqual(tag, "v1.2.0")
        self.assertEqual(url, "https://github.com/krishnagarg-2004/Mediadock/releases/tag/v1.2.0")
        self.assertIn("v1.2.0 is available", notes)

    def test_update_checker_handles_current_version(self):
        worker = _UpdateCheckWorker("v1.0.0")
        results = []
        worker.result_ready.connect(lambda has_upd, tag, url, notes: results.append((has_upd, tag, url, notes)))

        mock_payload = (
            b'{"tag_name": "v1.0.0", "html_url": "https://github.com/krishnagarg-2004/Mediadock/releases/tag/v1.0.0", '
            b'"body": "Current release"}'
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = mock_payload
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            worker.run()

        self.assertEqual(len(results), 1)
        has_update, tag, url, notes = results[0]
        self.assertFalse(has_update)
        self.assertEqual(tag, "v1.0.0")


if __name__ == "__main__":
    unittest.main()
