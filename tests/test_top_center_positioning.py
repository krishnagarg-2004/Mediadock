"""Unit tests for Dynamic Island top-center window positioning and non-draggable behavior."""

import sys
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from src.core.settings import SettingsManager
from src.ui.frameless_window import FramelessWindow
from src.ui.main_window import MainWindow, TOP_OFFSET_PX, COLLAPSED_SIZE, EXPANDED_SIZE


class TestTopCenterPositioning(unittest.TestCase):
    """Test suite covering top-center positioning formula, drag-disabling, and geometry calculations."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a QApplication instance exists for GUI tests."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self) -> None:
        """Initialize clean SettingsManager and MainWindow for each test."""
        self.settings = SettingsManager()
        self.settings.clear()
        self.window = MainWindow(settings_manager=self.settings)

    def test_allow_drag_property_defaults_and_override(self) -> None:
        """Verify FramelessWindow default allow_drag is True, but MainWindow sets allow_drag=False."""
        fw = FramelessWindow()
        self.assertTrue(fw.allow_drag)

        self.assertFalse(self.window.allow_drag)

    def test_mouse_drag_events_ignored_when_allow_drag_false(self) -> None:
        """Verify mouse drag press/move events do not update window position when allow_drag is False."""
        self.window.update_top_center_position()
        initial_pos = self.window.pos()

        from PySide6.QtCore import QPointF

        # Simulate left mouse press & move
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.window.mousePressEvent(press_event)

        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(100, 100),
            QPointF(100, 100),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.window.mouseMoveEvent(move_event)

        # Window position must remain unchanged at initial top-center position
        self.assertEqual(self.window.pos(), initial_pos)

    @patch("PySide6.QtGui.QGuiApplication.primaryScreen")
    def test_compute_top_center_collapsed_geometry(self, mock_primary_screen) -> None:
        """Verify compute_top_center_collapsed_geometry centers DeskNotch collapsed bar at top work area + TOP_OFFSET_PX."""
        mock_screen = MagicMock()
        mock_screen.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
        mock_primary_screen.return_value = mock_screen

        rect = self.window.compute_top_center_collapsed_geometry()
        expected_x = (1920 - COLLAPSED_SIZE[0]) // 2
        expected_y = TOP_OFFSET_PX

        self.assertEqual(rect, QRect(expected_x, expected_y, COLLAPSED_SIZE[0], COLLAPSED_SIZE[1]))

    @patch("PySide6.QtGui.QGuiApplication.primaryScreen")
    def test_compute_top_center_expanded_geometry(self, mock_primary_screen) -> None:
        """Verify compute_top_center_expanded_geometry centers DeskNotch expanded card at top work area + TOP_OFFSET_PX."""
        mock_screen = MagicMock()
        mock_screen.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
        mock_primary_screen.return_value = mock_screen

        rect = self.window.compute_top_center_expanded_geometry()
        expected_x = (1920 - EXPANDED_SIZE[0]) // 2
        expected_y = TOP_OFFSET_PX

        self.assertEqual(rect, QRect(expected_x, expected_y, EXPANDED_SIZE[0], EXPANDED_SIZE[1]))

    def test_position_not_restored_from_legacy_pos_x_pos_y_settings(self) -> None:
        """Verify window position always initializes at top-center position."""
        new_window = MainWindow(settings_manager=self.settings)
        new_window.show()

        # Position must be centered at TOP_OFFSET_PX
        self.assertEqual(new_window.pos().y(), TOP_OFFSET_PX)

    def test_main_window_constructible_and_media_slots_working(self) -> None:
        """Verify existing MainWindow transport controls and track update slots function normally."""
        from src.core.models import TrackInfo, PlaybackStatus

        track = TrackInfo(title="Test Song", artist="Test Artist")
        self.window.on_track_changed(track)
        self.assertEqual(self.window.title_label.full_text(), "Test Song")
        self.assertEqual(self.window.artist_label.full_text(), "Test Artist")

        self.window.on_status_changed(PlaybackStatus.PLAYING)
        self.assertEqual(self.window._current_status, PlaybackStatus.PLAYING)

    def test_lifecycle_show_hide_intact(self) -> None:
        """Verify show() and hide() transitions operate cleanly with top-center geometry."""
        self.window.show()
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.pos().y(), TOP_OFFSET_PX)

        self.window.hide()
        self.assertFalse(self.window.isVisible())

    def test_show_event_initial_collapsed_geometry_centered(self) -> None:
        """Verify showEvent calculates initial geometry using 180x40 collapsed dimensions with center X equal to screen center X."""
        from PySide6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        expected_screen_cx = screen_geom.left() + screen_geom.width() / 2.0
        expected_collapsed_x = screen_geom.left() + (screen_geom.width() - COLLAPSED_SIZE[0]) // 2

        self.window.show()
        self.app.processEvents()

        geom = self.window.geometry()
        win_cx = geom.x() + geom.width() / 2.0

        self.assertEqual(geom.width(), COLLAPSED_SIZE[0])
        self.assertEqual(geom.height(), COLLAPSED_SIZE[1])
        self.assertEqual(geom.y(), TOP_OFFSET_PX)
        self.assertEqual(geom.x(), expected_collapsed_x)
        self.assertEqual(win_cx, expected_screen_cx)

    def test_repeated_expand_collapse_cycles_preserve_center_x(self) -> None:
        """Verify 10 repeated expand/collapse cycles preserve exact center X coordinate with zero position drift."""
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import QEventLoop, QTimer
        from src.ui.main_window import DynamicIslandState

        screen = QGuiApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        expected_screen_cx = screen_geom.left() + screen_geom.width() / 2.0

        self.window.show()
        self.app.processEvents()

        initial_collapsed_geom = self.window.geometry()
        self.assertEqual(initial_collapsed_geom.x() + initial_collapsed_geom.width() / 2.0, expected_screen_cx)

        for cycle in range(1, 11):
            # 1. Expand transition
            self.window.set_state(DynamicIslandState.EXPANDED, animate=True)
            loop_exp = QEventLoop()
            self.window._geom_anim.finished.connect(loop_exp.quit)
            QTimer.singleShot(500, loop_exp.quit)
            loop_exp.exec()
            self.app.processEvents()

            exp_geom = self.window.geometry()
            self.assertEqual(exp_geom.width(), EXPANDED_SIZE[0])
            self.assertEqual(exp_geom.height(), EXPANDED_SIZE[1])
            self.assertEqual(exp_geom.y(), TOP_OFFSET_PX)
            self.assertEqual(exp_geom.x() + exp_geom.width() / 2.0, expected_screen_cx)

            # 2. Collapse transition
            self.window.set_state(DynamicIslandState.COLLAPSED, animate=True)
            loop_col = QEventLoop()
            self.window._geom_anim.finished.connect(loop_col.quit)
            QTimer.singleShot(500, loop_col.quit)
            loop_col.exec()
            self.app.processEvents()

            col_geom = self.window.geometry()
            self.assertEqual(col_geom.width(), COLLAPSED_SIZE[0])
            self.assertEqual(col_geom.height(), COLLAPSED_SIZE[1])
            self.assertEqual(col_geom.y(), TOP_OFFSET_PX)
            self.assertEqual(col_geom.x() + col_geom.width() / 2.0, expected_screen_cx)
            self.assertEqual(col_geom, initial_collapsed_geom, f"Drift detected at cycle {cycle}")

    def test_collapsed_metadata_vertical_alignment_preserved_after_collapse(self) -> None:
        """Verify collapsed metadata group center Y equals capsule center Y before and after expand/collapse cycle."""
        from PySide6.QtCore import QEventLoop, QTimer
        from src.ui.main_window import DynamicIslandState

        self.window.show()
        self.app.processEvents()

        capsule = self.window._capsule_widget
        initial_cap_cy = capsule.geometry().y() + capsule.geometry().height() / 2.0
        initial_title_cy = capsule.title_label.geometry().y() + capsule.title_label.geometry().height() / 2.0

        # Expand -> Collapse animation cycle
        self.window.set_state(DynamicIslandState.EXPANDED, animate=True)
        loop1 = QEventLoop()
        self.window._geom_anim.finished.connect(loop1.quit)
        QTimer.singleShot(500, loop1.quit)
        loop1.exec()
        self.app.processEvents()

        self.window.set_state(DynamicIslandState.COLLAPSED, animate=True)
        loop2 = QEventLoop()
        self.window._geom_anim.finished.connect(loop2.quit)
        QTimer.singleShot(500, loop2.quit)
        loop2.exec()
        self.app.processEvents()

        post_cap_geom = capsule.geometry()
        post_cap_cy = post_cap_geom.y() + post_cap_geom.height() / 2.0
        post_title_cy = capsule.title_label.geometry().y() + capsule.title_label.geometry().height() / 2.0
        post_icon_cy = capsule.icon_label.geometry().y() + capsule.icon_label.geometry().height() / 2.0
        post_dot_cy = capsule.status_dot.geometry().y() + capsule.status_dot.geometry().height() / 2.0

        self.assertEqual(post_cap_geom.width(), COLLAPSED_SIZE[0])
        self.assertEqual(post_cap_geom.height(), COLLAPSED_SIZE[1])
        self.assertEqual(post_cap_cy, COLLAPSED_SIZE[1] / 2.0)
        self.assertEqual(post_title_cy, post_cap_cy)
        self.assertEqual(post_icon_cy, post_cap_cy)
        self.assertEqual(post_dot_cy, post_cap_cy)

    def test_collapsed_to_expanded_animation_center_x_constant(self) -> None:
        """Verify window center X remains strictly constant and equal to screen center X throughout COLLAPSED -> EXPANDED."""
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import QEventLoop, QTimer, QRect
        from src.ui.main_window import DynamicIslandState

        screen = QGuiApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        screen_cx = screen_geom.left() + screen_geom.width() / 2.0

        self.window.show()
        self.app.processEvents()

        frame_center_xs = []

        def track_frame_geometry(val):
            if isinstance(val, QRect):
                frame_cx = val.x() + val.width() / 2.0
                frame_center_xs.append(frame_cx)

        self.window._geom_anim.valueChanged.connect(track_frame_geometry)
        self.window.set_state(DynamicIslandState.EXPANDED, animate=True)

        loop = QEventLoop()
        self.window._geom_anim.finished.connect(loop.quit)
        QTimer.singleShot(500, loop.quit)
        loop.exec()
        self.app.processEvents()

        self.window._geom_anim.valueChanged.disconnect(track_frame_geometry)

        for cx in frame_center_xs:
            self.assertEqual(cx, screen_cx)


if __name__ == "__main__":
    unittest.main()
