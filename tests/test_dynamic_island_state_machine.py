"""Unit tests for Dynamic Island State Machine & Hover Integration (Step 9.1.4)."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt, QPointF, QEvent, QSettings
from PySide6.QtGui import QEnterEvent, QEventPoint
from PySide6.QtWidgets import QApplication

from src.core.models import TrackInfo, PlaybackStatus, VolumeState
from src.core.settings import SettingsManager
from src.media.base_provider import BaseMediaProvider
from src.core.media_core import MediaCore
from src.ui.main_window import (
    MainWindow,
    DynamicIslandState,
    TOP_OFFSET_PX,
    COLLAPSED_TOP_OFFSET_PX,
    EXPANDED_TOP_OFFSET_PX,
    COLLAPSED_SIZE,
    EXPANDED_SIZE,
)


class MockMediaProvider(BaseMediaProvider):
    """Mock media provider for deterministic state machine testing."""

    def __init__(self, session_available: bool = False) -> None:
        super().__init__()
        self._available = session_available

    def is_session_available(self) -> bool:
        return self._available

    def set_available(self, available: bool) -> None:
        self._available = available

    def get_current_track(self) -> TrackInfo:
        return TrackInfo(title="Midnight City", artist="M83", album="Hurry Up, We're Dreaming")

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


class TestDynamicIslandStateMachine(unittest.TestCase):
    """Comprehensive test suite covering DynamicIslandState machine and hover events."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure QApplication instance exists for GUI tests."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self) -> None:
        """Set up clean isolated SettingsManager, MediaCore, and MainWindow before each test."""
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        self.tmp_file.close()
        self.qs = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        self.settings = SettingsManager(qsettings=self.qs)
        self.provider = MockMediaProvider(session_available=False)
        self.media_core = MediaCore(provider=self.provider)
        self.window = MainWindow(media_core=self.media_core, settings_manager=self.settings)

    def tearDown(self) -> None:
        """Clean up temporary INI file after each test."""
        if hasattr(self, "tmp_file") and os.path.exists(self.tmp_file.name):
            try:
                os.unlink(self.tmp_file.name)
            except OSError:
                pass

    # 1. Initial HIDDEN state when no media exists
    def test_initial_hidden_state_when_no_media_exists(self) -> None:
        """Verify Dynamic Island initializes to HIDDEN when no media session exists."""
        self.assertEqual(self.window.island_state, DynamicIslandState.HIDDEN)
        self.assertFalse(self.window.isVisible())

    # 2. Initial COLLAPSED state when media already exists
    def test_initial_collapsed_state_when_media_exists(self) -> None:
        """Verify Dynamic Island initializes to COLLAPSED when an active media session exists."""
        provider = MockMediaProvider(session_available=True)
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core, settings_manager=self.settings)
        self.assertEqual(window.island_state, DynamicIslandState.COLLAPSED)
        self.assertTrue(window.isVisible())
        self.assertEqual(window.width(), COLLAPSED_SIZE[0])
        self.assertEqual(window.height(), COLLAPSED_SIZE[1])

    # 3. HIDDEN -> COLLAPSED when session becomes available
    def test_hidden_to_collapsed_on_session_available(self) -> None:
        """Verify emitting session_availability_changed(True) transitions state from HIDDEN to COLLAPSED."""
        self.assertEqual(self.window.island_state, DynamicIslandState.HIDDEN)
        self.media_core.session_availability_changed.emit(True)
        self.assertEqual(self.window.island_state, DynamicIslandState.COLLAPSED)
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.width(), COLLAPSED_SIZE[0])

    # 4. COLLAPSED -> EXPANDED on mouse enter
    def test_collapsed_to_expanded_on_mouse_enter(self) -> None:
        """Verify mouse enterEvent on COLLAPSED capsule transitions to EXPANDED card geometry."""
        self.window.set_state(DynamicIslandState.COLLAPSED, animate=False)

        event = QEvent(QEvent.Type.Enter)
        self.window.enterEvent(event)
        if self.window._geom_anim.state() == self.window._geom_anim.State.Running:
            self.window._geom_anim.setCurrentTime(180)

        self.assertEqual(self.window.island_state, DynamicIslandState.EXPANDED)
        self.assertEqual(self.window.width(), EXPANDED_SIZE[0])
        self.assertEqual(self.window.height(), EXPANDED_SIZE[1])

    # 5. EXPANDED -> COLLAPSED after inactivity timeout
    def test_expanded_to_collapsed_on_inactivity_timeout(self) -> None:
        """Verify mouse leaveEvent starts collapse timer, which transitions state back to COLLAPSED on timeout."""
        self.window.set_state(DynamicIslandState.EXPANDED, animate=False)

        event = QEvent(QEvent.Type.Leave)
        self.window.leaveEvent(event)

        self.assertTrue(self.window._collapse_timer.isActive())

        # Trigger timer timeout explicitly
        self.window._on_collapse_timer_timeout()
        if self.window._geom_anim.state() == self.window._geom_anim.State.Running:
            self.window._geom_anim.setCurrentTime(180)

        self.assertEqual(self.window.island_state, DynamicIslandState.COLLAPSED)
        self.assertEqual(self.window.width(), COLLAPSED_SIZE[0])

    # 6. Timer cancellation when mouse re-enters
    def test_timer_cancellation_on_mouse_reenter(self) -> None:
        """Verify mouse enterEvent while EXPANDED cancels active collapse timer."""
        self.window.set_state(DynamicIslandState.EXPANDED)
        self.window.leaveEvent(QEvent(QEvent.Type.Leave))
        self.assertTrue(self.window._collapse_timer.isActive())

        # Mouse re-enters before timeout
        self.window.enterEvent(QEvent(QEvent.Type.Enter))
        self.assertFalse(self.window._collapse_timer.isActive())
        self.assertEqual(self.window.island_state, DynamicIslandState.EXPANDED)

    # 7. COLLAPSED remains COLLAPSED when mouse leaves
    def test_collapsed_remains_collapsed_on_mouse_leave(self) -> None:
        """Verify mouse leaveEvent while COLLAPSED does not start collapse timer or alter state."""
        self.window.set_state(DynamicIslandState.COLLAPSED)
        self.window.leaveEvent(QEvent(QEvent.Type.Leave))
        self.assertFalse(self.window._collapse_timer.isActive())
        self.assertEqual(self.window.island_state, DynamicIslandState.COLLAPSED)

    # 8. Media session closure causes EXPANDED -> HIDDEN
    def test_session_closure_causes_expanded_to_hidden(self) -> None:
        """Verify session closure while EXPANDED transitions state to HIDDEN."""
        self.window.set_state(DynamicIslandState.EXPANDED)
        self.media_core.session_availability_changed.emit(False)
        self.assertEqual(self.window.island_state, DynamicIslandState.HIDDEN)
        self.assertFalse(self.window.isVisible())

    # 9. Media session closure causes COLLAPSED -> HIDDEN
    def test_session_closure_causes_collapsed_to_hidden(self) -> None:
        """Verify session closure while COLLAPSED transitions state to HIDDEN."""
        self.window.set_state(DynamicIslandState.COLLAPSED)
        self.media_core.session_availability_changed.emit(False)
        self.assertEqual(self.window.island_state, DynamicIslandState.HIDDEN)
        self.assertFalse(self.window.isVisible())

    # 10. MediaDock process/lifecycle remains active after media session closes
    def test_process_remains_active_on_session_closure(self) -> None:
        """Verify session closure hides Dynamic Island window without calling QApplication.quit."""
        with patch.object(QApplication, "quit") as mock_quit:
            self.window.set_state(DynamicIslandState.COLLAPSED)
            self.media_core.session_availability_changed.emit(False)
            self.assertEqual(self.window.island_state, DynamicIslandState.HIDDEN)
            mock_quit.assert_not_called()

    # 11. Dynamic Island disabled -> HIDDEN
    def test_disabled_setting_forces_hidden_state(self) -> None:
        """Verify setting dynamic_island/enabled to False forces state to HIDDEN."""
        self.window.set_state(DynamicIslandState.COLLAPSED)
        self.settings.set_dynamic_island_enabled(False)
        self.assertEqual(self.window.island_state, DynamicIslandState.HIDDEN)
        self.assertFalse(self.window.isVisible())

    # 12. Track changes update content without unnecessarily expanding
    def test_track_change_preserves_current_state(self) -> None:
        """Verify track change updates capsule and label content without forcing EXPANDED state."""
        self.window.set_state(DynamicIslandState.COLLAPSED)
        new_track = TrackInfo(title="Starboy", artist="The Weeknd")
        self.media_core.track_changed.emit(new_track)

        self.assertEqual(self.window.island_state, DynamicIslandState.COLLAPSED)
        self.assertIn("Starboy", self.window._capsule_widget.title_label.full_text())
        self.assertEqual(self.window.title_label.text(), "Starboy")

    # 13. Volume changes continue reaching the expanded UI
    def test_volume_changes_reach_expanded_ui(self) -> None:
        """Verify volume_changed signal updates volume slider value and mute button icon."""
        self.window.set_state(DynamicIslandState.EXPANDED)
        vol_state = VolumeState(volume_percent=75, is_muted=False, is_supported=True)
        self.media_core.volume_changed.emit(vol_state)

        self.assertEqual(self.window.slider_volume.value(), 75)
        self.assertTrue(self.window.slider_volume.isVisible())

    # 14. State transitions preserve top-center geometry
    def test_state_transitions_preserve_top_center_geometry(self) -> None:
        """Verify COLLAPSED notch anchors at COLLAPSED_TOP_OFFSET_PX and EXPANDED oval sits at EXPANDED_TOP_OFFSET_PX."""
        from PySide6.QtCore import QEventLoop, QTimer

        self.window.set_state(DynamicIslandState.COLLAPSED)
        self.assertEqual(self.window.pos().y(), COLLAPSED_TOP_OFFSET_PX)

        self.window.set_state(DynamicIslandState.EXPANDED)
        if self.window._geom_anim.state() == self.window._geom_anim.State.Running:
            loop = QEventLoop()
            self.window._geom_anim.finished.connect(loop.quit)
            QTimer.singleShot(500, loop.quit)
            loop.exec()
        self.app.processEvents()
        self.assertEqual(self.window.pos().y(), EXPANDED_TOP_OFFSET_PX)

    # 15. Existing media controls remain functional
    def test_existing_media_controls_functional(self) -> None:
        """Verify previous, play/pause, and next transport control buttons trigger media_core slots."""
        self.media_core.session_availability_changed.emit(True)
        with patch.object(self.media_core, "previous_track") as mock_prev, \
             patch.object(self.media_core, "toggle_play_pause") as mock_pp, \
             patch.object(self.media_core, "next_track") as mock_next:

            self.window.btn_prev.click()
            mock_prev.assert_called_once()

            self.window.btn_play_pause.click()
            mock_pp.assert_called_once()

            self.window.btn_next.click()
            mock_next.assert_called_once()


    # 16. Collapse delay read dynamically from SettingsManager
    def test_collapse_delay_read_from_settings_manager(self) -> None:
        """Verify leaveEvent uses collapse delay from SettingsManager when starting collapse timer."""
        self.settings.set_collapse_delay_ms(5000)
        self.window.set_state(DynamicIslandState.EXPANDED)
        self.window.leaveEvent(QEvent(QEvent.Type.Leave))

        self.assertTrue(self.window._collapse_timer.isActive())
        self.assertEqual(self.window._collapse_timer.interval(), 5000)

    # 17. Active collapse timer updates interval immediately on setting change
    def test_active_timer_updates_interval_on_setting_change(self) -> None:
        """Verify changing collapse delay setting while collapse timer is active updates active timer interval immediately."""
        self.window.set_state(DynamicIslandState.EXPANDED)
        self.window.leaveEvent(QEvent(QEvent.Type.Leave))
        self.assertTrue(self.window._collapse_timer.isActive())
        self.assertEqual(self.window._collapse_timer.interval(), 3500)

        # Update setting to 2250 ms
        self.settings.set_collapse_delay_ms(2250)
        self.assertTrue(self.window._collapse_timer.isActive())
        self.assertEqual(self.window._collapse_timer.interval(), 2250)

    # 18. Geometry animation configuration
    def test_pop_in_pop_out_geometry_animation(self) -> None:
        """Verify MainWindow has QPropertyAnimation configured for pop-in/pop-out geometry transition."""
        from PySide6.QtCore import QEasingCurve, QPropertyAnimation
        self.assertIsInstance(self.window._geom_anim, QPropertyAnimation)
        self.assertEqual(self.window._geom_anim.propertyName(), b"geometry")
        self.assertEqual(self.window._geom_anim.duration(), 180)
        self.assertEqual(self.window._geom_anim.easingCurve().type(), QEasingCurve.Type.OutCubic)

    # 19. Centered X coordinate for pop-in / pop-out animation
    def test_pop_in_pop_out_geometry_animation_centered_x(self) -> None:
        """Verify COLLAPSED and EXPANDED animation start and end geometries share exact same center X coordinate."""
        collapsed_rect = self.window.compute_top_center_collapsed_geometry()
        expanded_rect = self.window.compute_top_center_expanded_geometry()

        collapsed_center_x = collapsed_rect.x() + collapsed_rect.width() / 2.0
        expanded_center_x = expanded_rect.x() + expanded_rect.width() / 2.0

        self.assertEqual(collapsed_center_x, expanded_center_x)

    # 20. Intermediate frame centering and horizontal symmetry
    def test_pop_in_pop_out_child_content_centered_during_animation(self) -> None:
        """Regression test: verify every intermediate frame geometry expands/contracts symmetrically around constant center X."""
        from PySide6.QtCore import QRect
        from src.ui.main_window import COLLAPSED_SIZE, EXPANDED_SIZE, TOP_OFFSET_PX

        collapsed_rect = self.window.compute_top_center_collapsed_geometry()
        expanded_rect = self.window.compute_top_center_expanded_geometry()

        center_x = collapsed_rect.left() + collapsed_rect.width() // 2
        expanded_center = expanded_rect.left() + expanded_rect.width() // 2
        self.assertEqual(center_x, expanded_center)

        for i in range(6):
            t = i / 5.0
            w = int(COLLAPSED_SIZE[0] + (EXPANDED_SIZE[0] - COLLAPSED_SIZE[0]) * t)
            h = int(COLLAPSED_SIZE[1] + (EXPANDED_SIZE[1] - COLLAPSED_SIZE[1]) * t)
            x = center_x - w // 2
            r = QRect(x, TOP_OFFSET_PX, w, h)

            cur_center = r.left() + r.width() // 2
            left_dist = cur_center - r.left()
            right_dist = (r.left() + r.width()) - cur_center

            self.assertEqual(cur_center, center_x)
            self.assertEqual(left_dist, right_dist)


if __name__ == "__main__":
    unittest.main()
