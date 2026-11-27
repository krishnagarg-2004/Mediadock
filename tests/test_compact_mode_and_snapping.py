"""Unit tests for Compact Mode View and Desktop Edge Snapping in MediaDock."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from PySide6.QtCore import Qt, QPoint, QRect, QSettings
from PySide6.QtWidgets import QApplication

from src.core.models import TrackInfo, PlaybackStatus
from src.core.settings import SettingsManager
from src.media.base_provider import BaseMediaProvider
from src.core.media_core import MediaCore
from src.ui.frameless_window import FramelessWindow, SNAP_THRESHOLD_PX
from src.ui.main_window import MainWindow

# Ensure QApplication instance exists for GUI tests
_app = QApplication.instance() or QApplication([])


class DummyMediaProvider(BaseMediaProvider):
    """Dummy media provider for testing."""

    def __init__(self, available: bool = False) -> None:
        super().__init__()
        self._available = available

    def is_session_available(self) -> bool:
        return self._available

    def get_current_track(self) -> TrackInfo:
        return TrackInfo(
            title="A Very Long Song Title That Exceeds Widget Width Bound",
            artist="A Popular Artist Name",
            album="Test Album",
        )

    def get_playback_status(self) -> PlaybackStatus:
        return PlaybackStatus.PLAYING if self._available else PlaybackStatus.CLOSED

    def start_listening(self) -> None:
        pass

    def stop_listening(self) -> None:
        pass

    def set_on_track_changed(self, callback) -> None:
        pass

    def set_on_status_changed(self, callback) -> None:
        pass

    def set_on_session_availability_changed(self, callback) -> None:
        pass

    def play(self) -> bool:
        return True

    def pause(self) -> bool:
        return True

    def toggle_play_pause(self) -> bool:
        return True

    def next_track(self) -> bool:
        return True

    def previous_track(self) -> bool:
        return True

    def seek_to_position(self, position_ms: int) -> bool:
        return True


class TestCompactModeAndEdgeSnapping(unittest.TestCase):
    """Comprehensive test suite covering Compact Mode and Desktop Edge Snapping."""

    def setUp(self) -> None:
        """Create clean isolated SettingsManager and MainWindow for each test."""
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        self.tmp_file.close()
        self.qs = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        self.settings = SettingsManager(qsettings=self.qs)
        self.provider = DummyMediaProvider(available=False)
        self.media_core = MediaCore(provider=self.provider)
        self.window = MainWindow(media_core=self.media_core, settings_manager=self.settings)

    def tearDown(self) -> None:
        """Clean up temporary INI file after each test."""
        if hasattr(self, "tmp_file") and os.path.exists(self.tmp_file.name):
            try:
                os.unlink(self.tmp_file.name)
            except OSError:
                pass

    # --- 1. Compact Mode Persistence & Default ---

    def test_compact_mode_default_value(self) -> None:
        """Verify compact_mode defaults to False."""
        self.assertFalse(self.settings.get_compact_mode())
        self.assertFalse(self.window.is_compact_mode)

    def test_compact_mode_persistence(self) -> None:
        """Verify set_compact_mode wrapper maps True to COLLAPSED geometry."""
        from src.ui.main_window import COLLAPSED_SIZE
        self.settings.set_compact_mode(True)
        self.assertTrue(self.settings.get_compact_mode())

        # Re-instantiate window
        new_window = MainWindow(media_core=self.media_core, settings_manager=self.settings)
        new_window.set_compact_mode(True)
        self.assertTrue(new_window.is_compact_mode)
        self.assertEqual(new_window.width(), COLLAPSED_SIZE[0])
        self.assertEqual(new_window.height(), COLLAPSED_SIZE[1])

    # --- 2. Switching Modes & Dimensions ---

    def test_switch_full_to_compact_dimensions_and_visibility(self) -> None:
        """Verify set_compact_mode(True) maps to COLLAPSED geometry (180x40 px)."""
        from src.ui.main_window import COLLAPSED_SIZE, EXPANDED_SIZE
        self.window.set_state(self.window.island_state.EXPANDED, animate=False)
        self.assertEqual(self.window.width(), EXPANDED_SIZE[0])
        self.assertEqual(self.window.height(), EXPANDED_SIZE[1])

        self.window.set_compact_mode(True)
        if self.window._geom_anim.state() == self.window._geom_anim.State.Running:
            self.window._geom_anim.setCurrentTime(180)
        self.assertTrue(self.window.is_compact_mode)
        self.assertEqual(self.window.width(), COLLAPSED_SIZE[0])
        self.assertEqual(self.window.height(), COLLAPSED_SIZE[1])

    def test_switch_compact_to_full_restores_dimensions_and_widgets(self) -> None:
        """Verify switching Compact -> Full restores EXPANDED geometry (360x160 px)."""
        from src.ui.main_window import EXPANDED_SIZE
        self.window.set_compact_mode(True)
        self.window.set_compact_mode(False)
        if self.window._geom_anim.state() == self.window._geom_anim.State.Running:
            self.window._geom_anim.setCurrentTime(180)

        self.assertFalse(self.window.is_compact_mode)
        self.assertEqual(self.window.width(), EXPANDED_SIZE[0])
        self.assertEqual(self.window.height(), EXPANDED_SIZE[1])

    def test_long_title_elision_in_compact_mode(self) -> None:
        """Verify long track titles are elided cleanly in compact mode without crash."""
        self.window.set_compact_mode(True)
        self.window.on_track_changed(self.provider.get_current_track())
        self.assertTrue(self.window.title_label.text().startswith("A Very Long"))
        self.assertIn("A Very Long Song Title", self.window.title_label.full_text())


    # --- 3. Edge Snapping Math Tests ---

    @patch("PySide6.QtGui.QGuiApplication.screenAt")
    @patch("PySide6.QtGui.QGuiApplication.primaryScreen")
    def test_left_edge_snapping_within_threshold(self, mock_primary, mock_screen_at) -> None:
        """Verify window snaps to left screen edge (x = availableGeometry.left()) within 15px."""
        mock_screen = MagicMock()
        mock_screen.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
        mock_primary.return_value = mock_screen
        mock_screen_at.return_value = mock_screen

        raw_pos = QPoint(10, 200)
        snapped = self.window._apply_edge_snapping(raw_pos)

        self.assertEqual(snapped.x(), 0)
        self.assertEqual(snapped.y(), 200)

    @patch("PySide6.QtGui.QGuiApplication.screenAt")
    @patch("PySide6.QtGui.QGuiApplication.primaryScreen")
    def test_right_edge_snapping_within_threshold(self, mock_primary, mock_screen_at) -> None:
        """Verify window snaps to right screen edge (x + width = availableGeometry.right()) within 15px."""
        mock_screen = MagicMock()
        mock_screen.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
        mock_primary.return_value = mock_screen
        mock_screen_at.return_value = mock_screen

        win_w = self.window.width()
        raw_x = 1915 - win_w
        raw_pos = QPoint(raw_x, 300)
        snapped = self.window._apply_edge_snapping(raw_pos)

        self.assertEqual(snapped.x(), 1919 - win_w)
        self.assertEqual(snapped.y(), 300)

    @patch("PySide6.QtGui.QGuiApplication.screenAt")
    @patch("PySide6.QtGui.QGuiApplication.primaryScreen")
    def test_top_edge_snapping_within_threshold(self, mock_primary, mock_screen_at) -> None:
        """Verify window snaps to top screen edge (y = availableGeometry.top()) within 15px."""
        mock_screen = MagicMock()
        mock_screen.availableGeometry.return_value = QRect(0, 30, 1920, 1050)
        mock_primary.return_value = mock_screen
        mock_screen_at.return_value = mock_screen

        raw_pos = QPoint(400, 35)
        snapped = self.window._apply_edge_snapping(raw_pos)

        self.assertEqual(snapped.x(), 400)
        self.assertEqual(snapped.y(), 30)

    @patch("PySide6.QtGui.QGuiApplication.screenAt")
    @patch("PySide6.QtGui.QGuiApplication.primaryScreen")
    def test_bottom_edge_snapping_within_threshold(self, mock_primary, mock_screen_at) -> None:
        """Verify window snaps to bottom screen edge (y + height = availableGeometry.bottom()) within 15px."""
        mock_screen = MagicMock()
        mock_screen.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
        mock_primary.return_value = mock_screen
        mock_screen_at.return_value = mock_screen

        win_h = self.window.height()
        raw_y = 1075 - win_h
        raw_pos = QPoint(500, raw_y)
        snapped = self.window._apply_edge_snapping(raw_pos)

        self.assertEqual(snapped.x(), 500)
        self.assertEqual(snapped.y(), 1079 - win_h)

    @patch("PySide6.QtGui.QGuiApplication.screenAt")
    @patch("PySide6.QtGui.QGuiApplication.primaryScreen")
    def test_no_snap_outside_15px_threshold(self, mock_primary, mock_screen_at) -> None:
        """Verify window position is unchanged when outside 15px snap threshold."""
        mock_screen = MagicMock()
        mock_screen.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
        mock_primary.return_value = mock_screen
        mock_screen_at.return_value = mock_screen

        # raw_x = 50 (35px from 0, threshold is 15px)
        raw_pos = QPoint(50, 200)
        snapped = self.window._apply_edge_snapping(raw_pos)

        self.assertEqual(snapped.x(), 50)
        self.assertEqual(snapped.y(), 200)

    @patch("PySide6.QtGui.QGuiApplication.screenAt")
    @patch("PySide6.QtGui.QGuiApplication.primaryScreen")
    def test_multi_monitor_edge_snapping_uses_correct_screen_bounds(self, mock_primary, mock_screen_at) -> None:
        """Verify edge snapping targets second monitor bounds when window center falls in screen 2."""
        mock_screen2 = MagicMock()
        mock_screen2.availableGeometry.return_value = QRect(1920, 0, 1920, 1080)
        mock_primary.return_value = MagicMock(availableGeometry=lambda: QRect(0, 0, 1920, 1080))
        mock_screen_at.return_value = mock_screen2

        raw_pos = QPoint(1930, 400)
        snapped = self.window._apply_edge_snapping(raw_pos)

        self.assertEqual(snapped.x(), 1920)
        self.assertEqual(snapped.y(), 400)

    # --- 4. Compact Mode + Edge Snapping Interaction ---

    @patch("PySide6.QtGui.QGuiApplication.screenAt")
    @patch("PySide6.QtGui.QGuiApplication.primaryScreen")
    def test_compact_mode_edge_snapping_interaction(self, mock_primary, mock_screen_at) -> None:
        """Verify compact mode (180x40) snaps correctly to edges."""
        from src.ui.main_window import COLLAPSED_SIZE
        mock_screen = MagicMock()
        mock_screen.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
        mock_primary.return_value = mock_screen
        mock_screen_at.return_value = mock_screen

        self.window.set_compact_mode(True)
        self.assertEqual(self.window.width(), COLLAPSED_SIZE[0])
        self.assertEqual(self.window.height(), COLLAPSED_SIZE[1])

        raw_x = 1915 - COLLAPSED_SIZE[0]
        raw_pos = QPoint(raw_x, 100)
        snapped = self.window._apply_edge_snapping(raw_pos)

        self.assertEqual(snapped.x(), 1919 - COLLAPSED_SIZE[0])


if __name__ == "__main__":
    unittest.main()
