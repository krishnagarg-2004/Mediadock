"""Unit tests for Phase 9.2.2 SVG Icon Architecture and Pure Black Visual Baseline."""

import sys
import unittest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from src.core.models import TrackInfo, PlaybackStatus, MediaSessionInfo
from src.ui.theme import (
    COLOR_BG_ISLAND,
    COLOR_STATUS_ACTIVE,
    COLOR_STATUS_INACTIVE,
    get_svg_pixmap,
    get_svg_icon,
)
from src.ui.components_island import CollapsedCapsuleWidget
from src.ui.main_window import MainWindow


class TestSvgIconsAndVisualBaseline(unittest.TestCase):
    """Test suite for SVG icon loading, fallback handling, pure black backgrounds, and status dot colors."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a single QApplication instance exists for Qt widgets."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_svg_icon_loading(self) -> None:
        """Verify get_svg_pixmap and get_svg_icon load valid non-null vector icons."""
        icon_names = [
            "play",
            "pause",
            "previous",
            "next",
            "volume",
            "mute",
            "spotify",
            "youtube",
            "vlc",
            "default_media",
        ]
        for name in icon_names:
            pix = get_svg_pixmap(name, size=24, color=QColor("#FFFFFF"))
            self.assertIsInstance(pix, QPixmap)
            self.assertFalse(pix.isNull())
            self.assertEqual(pix.width(), 24)
            self.assertEqual(pix.height(), 24)

            icon = get_svg_icon(name, size=24, color=QColor("#FFFFFF"))
            self.assertIsInstance(icon, QIcon)
            self.assertFalse(icon.isNull())

    def test_missing_icon_fallback(self) -> None:
        """Verify requesting a missing icon name falls back safely to default_media without crashing."""
        pix = get_svg_pixmap("non_existent_app_icon_xyz", size=24)
        self.assertIsInstance(pix, QPixmap)
        self.assertFalse(pix.isNull())

        icon = get_svg_icon("non_existent_app_icon_xyz", size=24)
        self.assertIsInstance(icon, QIcon)
        self.assertFalse(icon.isNull())

    def test_capsule_pure_black_background(self) -> None:
        """Verify CollapsedCapsuleWidget background color is pure black #000000."""
        capsule = CollapsedCapsuleWidget()
        self.assertEqual(capsule._bg_color.name(), "#000000")
        self.assertEqual(capsule.width(), 180)
        self.assertEqual(capsule.height(), 40)

    def test_capsule_status_dot_colors(self) -> None:
        """Verify status dot sets GREEN (#00FF7F) for PLAYING and RED (#C1121C) for INACTIVE."""
        capsule = CollapsedCapsuleWidget()

        # PLAYING -> GREEN
        capsule.set_playback_status(PlaybackStatus.PLAYING)
        self.assertIn("#00ff7f", capsule.status_dot.styleSheet().lower())

        # PAUSED / STOPPED / CLOSED -> RED
        capsule.set_playback_status(PlaybackStatus.PAUSED)
        self.assertIn("#c1121c", capsule.status_dot.styleSheet().lower())

        capsule.set_playback_status(PlaybackStatus.STOPPED)
        self.assertIn("#c1121c", capsule.status_dot.styleSheet().lower())

        capsule.set_playback_status(PlaybackStatus.CLOSED)
        self.assertIn("#c1121c", capsule.status_dot.styleSheet().lower())

    def test_capsule_source_aware_formatting(self) -> None:
        """Verify capsule displays source-aware text formatting for Spotify, YouTube, and VLC."""
        capsule = CollapsedCapsuleWidget()

        # Spotify: Song — Artist
        capsule.set_source_info("Spotify.exe", "CAYENDO", "Frank Ocean")
        self.assertEqual(capsule.title_label.full_text(), "CAYENDO \u2014 Frank Ocean")

        # YouTube: Video title only (no forced empty artist dash)
        capsule.set_source_info("chrome.exe", "Lo-Fi Beats 24/7", "")
        self.assertEqual(capsule.title_label.full_text(), "Lo-Fi Beats 24/7")

        # VLC: File name only
        capsule.set_source_info("vlc.exe", "Movie.mkv", "")
        self.assertEqual(capsule.title_label.full_text(), "Movie.mkv")

    def test_expanded_pure_black_background(self) -> None:
        """Verify MainWindow / FramelessWindow background is pure black #000000 and 360x160 px when expanded."""
        window = MainWindow()
        window.set_state(window.DynamicIslandState.EXPANDED if hasattr(window, "DynamicIslandState") else None)
        from src.ui.main_window import DynamicIslandState
        window.set_state(DynamicIslandState.EXPANDED)
        self.assertEqual(window._bg_color.name(), "#000000")
        self.assertEqual(window.width(), 360)
        self.assertEqual(window.height(), 160)

    def test_media_controls_functional_with_svg_icons(self) -> None:
        """Verify transport control buttons have valid SVG icons attached and fire click slots."""
        mock_core = MagicMock()
        mock_core.get_current_track.return_value = TrackInfo("Title", "Artist", 180000, 0, None)
        mock_core.get_playback_status.return_value = PlaybackStatus.PAUSED
        mock_core.is_session_available.return_value = True
        mock_core.get_volume_state.return_value = MagicMock(is_supported=True, volume_percent=80, is_muted=False)
        mock_core.get_active_session_info.return_value = None

        window = MainWindow(media_core=mock_core)

        self.assertFalse(window.btn_prev.icon().isNull())
        self.assertFalse(window.btn_play_pause.icon().isNull())
        self.assertFalse(window.btn_next.icon().isNull())
        self.assertFalse(window.btn_mute.icon().isNull())

        window.btn_prev.click()
        mock_core.previous_track.assert_called_once()

        window.btn_play_pause.click()
        mock_core.toggle_play_pause.assert_called_once()

        window.btn_next.click()
        mock_core.next_track.assert_called_once()


if __name__ == "__main__":
    unittest.main()
