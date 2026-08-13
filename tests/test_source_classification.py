"""Unit tests for live media source identification, normalized source classification, and capsule SVG icons."""

import sys
import unittest
from unittest.mock import MagicMock
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from src.core.models import TrackInfo, PlaybackStatus, MediaSessionInfo
from src.ui.components_island import CollapsedCapsuleWidget, classify_media_source
from src.ui.main_window import MainWindow


class TestSourceClassification(unittest.TestCase):
    """Test suite covering media source classification, Windows Store IDs, VLC, YouTube, and fallbacks."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure QApplication instance exists for GUI tests."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_spotify_desktop_app_id_classification(self) -> None:
        """Verify desktop Spotify app IDs resolve to 'spotify' source."""
        self.assertEqual(classify_media_source("Spotify.exe", "Song", "Artist"), "spotify")
        self.assertEqual(classify_media_source("spotify.exe", "Song", "Artist"), "spotify")
        self.assertEqual(classify_media_source("Spotify", "Song", "Artist"), "spotify")

    def test_spotify_windows_store_app_id_classification(self) -> None:
        """Verify Windows Store Spotify app IDs resolve to 'spotify' source."""
        self.assertEqual(
            classify_media_source("SpotifyAB.SpotifyMusic_zwe1h2g855e4g!Spotify", "Song", "Artist"),
            "spotify",
        )
        self.assertEqual(
            classify_media_source("Spotify_8wekyb3d8bbwe!Spotify", "Song", "Artist"),
            "spotify",
        )

    def test_vlc_classification(self) -> None:
        """Verify VLC app IDs resolve to 'vlc' source."""
        self.assertEqual(classify_media_source("vlc.exe", "Movie.mp4", ""), "vlc")
        self.assertEqual(classify_media_source("VLC Media Player", "Video.mkv", ""), "vlc")

    def test_youtube_explicit_and_browser_classification(self) -> None:
        """Verify YouTube classification for explicit YouTube sources and browser tabs with YouTube metadata."""
        # Explicit source_name YouTube
        self.assertEqual(classify_media_source("YouTube", "Video Title", ""), "youtube")

        # Chrome with YouTube in title
        self.assertEqual(classify_media_source("chrome.exe", "Rick Astley - Never Gonna Give You Up - YouTube", ""), "youtube")
        self.assertEqual(classify_media_source("Google Chrome", "Lofi Beats - YouTube", ""), "youtube")

        # Edge with YouTube in title/artist
        self.assertEqual(classify_media_source("msedge.exe", "Cool Music", "YouTube Channel"), "youtube")

        # Browser WITHOUT YouTube metadata should NOT be classified as youtube
        self.assertEqual(classify_media_source("chrome.exe", "Podcast Episode 1", "SoundCloud"), "default_media")
        self.assertEqual(classify_media_source("msedge.exe", "Random Article Reading", "News Site"), "default_media")

    def test_unknown_source_fallback(self) -> None:
        """Verify unknown or missing source identifiers fall back to 'default_media'."""
        self.assertEqual(classify_media_source("random_player.exe", "Track", "Artist"), "default_media")
        self.assertEqual(classify_media_source("", "Track", "Artist"), "default_media")
        self.assertEqual(classify_media_source("Unknown", "Track", "Artist"), "default_media")

    def test_capsule_icon_selection_and_text(self) -> None:
        """Verify CollapsedCapsuleWidget selects correct SVG icon name and sets elided title/artist text."""
        capsule = CollapsedCapsuleWidget()

        # 1. Spotify
        capsule.set_source_info("Spotify.exe", "Blinding Lights", "The Weeknd")
        self.assertEqual(capsule._current_icon_name, "spotify")
        self.assertEqual(capsule.title_label.full_text(), "Blinding Lights \u2014 The Weeknd")

        # 2. VLC
        capsule.set_source_info("vlc.exe", "Trailer.mov", "")
        self.assertEqual(capsule._current_icon_name, "vlc")
        self.assertEqual(capsule.title_label.full_text(), "Trailer.mov")

        # 3. YouTube
        capsule.set_source_info("chrome.exe", "Python Tutorial - YouTube", "")
        self.assertEqual(capsule._current_icon_name, "youtube")
        self.assertEqual(capsule.title_label.full_text(), "Python Tutorial - YouTube")

        # 4. Unknown
        capsule.set_source_info("unknown_app.exe", "Unknown Song", "Unknown Artist")
        self.assertEqual(capsule._current_icon_name, "default_media")
        self.assertEqual(capsule.title_label.full_text(), "Unknown Song \u2014 Unknown Artist")

    def test_main_window_session_and_track_app_id_fallback(self) -> None:
        """Verify MainWindow.on_track_changed uses MediaSessionInfo display_name/app_id, falling back to track.app_id."""
        mock_core = MagicMock()
        mock_core.get_current_track.return_value = TrackInfo("Track", "Artist", "Album", None, "Spotify.exe", 1000, 0)
        mock_core.get_playback_status.return_value = PlaybackStatus.PAUSED
        mock_core.is_session_available.return_value = True
        mock_core.get_volume_state.return_value = MagicMock(is_supported=True, volume_percent=50, is_muted=False)

        # Case A: Active MediaSessionInfo present with display_name
        mock_core.get_active_session_info.return_value = MediaSessionInfo(
            session_id="s1",
            app_id="SpotifyAB.SpotifyMusic_zwe1h2g855e4g!Spotify",
            display_name="Spotify",
        )
        window = MainWindow(media_core=mock_core)
        window.on_track_changed(TrackInfo("Starboy", "The Weeknd", "Starboy", None, "Spotify.exe", 200000, 0))
        self.assertEqual(window._capsule_widget._current_icon_name, "spotify")
        self.assertEqual(window._capsule_widget._current_source_name, "Spotify")

        # Case B: Active MediaSessionInfo is None -> fallback to track.app_id
        mock_core.get_active_session_info.return_value = None
        track_with_app = TrackInfo("Title", "Artist", "Album", None, "vlc.exe", 100000, 0)
        window.on_track_changed(track_with_app)
        self.assertEqual(window._capsule_widget._current_icon_name, "vlc")
        self.assertEqual(window._capsule_widget._current_source_name, "vlc.exe")


if __name__ == "__main__":
    unittest.main()
