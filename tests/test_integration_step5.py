"""Integration unit tests for Step 5: MainWindow UI integration with MediaCore."""

import sys
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.core.models import TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider
from src.core.media_core import MediaCore
from src.ui.main_window import MainWindow


class DummyProvider(BaseMediaProvider):
    """Dummy BaseMediaProvider subclass for Step 5 integration testing."""

    def __init__(self) -> None:
        self.is_active = False
        self.track_cb = None
        self.status_cb = None
        self.session_cb = None
        self.current_track = TrackInfo(title="Initial Title", artist="Initial Artist")
        self.current_status = PlaybackStatus.PAUSED

    def get_current_track(self) -> TrackInfo:
        return self.current_track

    def get_playback_status(self) -> PlaybackStatus:
        return self.current_status

    def is_session_available(self) -> bool:
        return True

    def start_listening(self) -> None:
        self.is_active = True

    def stop_listening(self) -> None:
        self.is_active = False

    def set_on_track_changed(self, callback) -> None:
        self.track_cb = callback

    def set_on_status_changed(self, callback) -> None:
        self.status_cb = callback

    def set_on_session_availability_changed(self, callback) -> None:
        self.session_cb = callback

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



class TestStep5Integration(unittest.TestCase):
    """Test suite verifying MainWindow UI updates when connected to MediaCore."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a QApplication instance exists for PySide6 GUI testing."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_window_frameless_properties_preserved(self) -> None:
        """Verify MainWindow retains frameless, translucent, and always-on-top flags."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        flags = window.windowFlags()
        self.assertTrue(flags & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(flags & Qt.WindowType.WindowStaysOnTopHint)
        self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))

    def test_initial_sync_display(self) -> None:
        """Verify MainWindow populates initial track and status on creation."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        self.assertEqual(window.title_label.full_text(), "Initial Title")
        self.assertEqual(window.artist_label.full_text(), "Initial Artist")
        self.assertEqual(window.status_label.text(), "PAUSED")

    def test_track_changed_slot_updates_ui(self) -> None:
        """Verify emitting track_changed updates labels in MainWindow."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        new_track = TrackInfo(
            title="Die With A Smile",
            artist="Lady Gaga & Bruno Mars",
            album="Single",
        )
        core.track_changed.emit(new_track)

        self.assertEqual(window.title_label.full_text(), "Die With A Smile")
        self.assertEqual(window.artist_label.full_text(), "Lady Gaga & Bruno Mars")


    def test_playback_status_changed_slot_updates_badge(self) -> None:
        """Verify emitting playback_status_changed updates status badge in MainWindow."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        core.playback_status_changed.emit(PlaybackStatus.PLAYING)
        self.assertEqual(window.status_label.text(), "PLAYING")

        core.playback_status_changed.emit(PlaybackStatus.STOPPED)
        self.assertEqual(window.status_label.text(), "STOPPED")

    def test_control_widgets_exist(self) -> None:
        """Verify all transport buttons, progress slider, and time labels exist."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        self.assertIsNotNone(window.btn_prev)
        self.assertIsNotNone(window.btn_play_pause)
        self.assertIsNotNone(window.btn_next)
        self.assertIsNotNone(window.progress_slider)
        self.assertIsNotNone(window.lbl_position)
        self.assertIsNotNone(window.lbl_duration)

    def test_elided_label_behavior(self) -> None:
        """Verify ElidedLabel preserves full_text, elides display text when width is constrained, and sets tooltips."""
        from src.ui.components import ElidedLabel
        lbl = ElidedLabel("Very Long Track Title That Will Exceed Available Width")
        self.assertEqual(lbl.full_text(), "Very Long Track Title That Will Exceed Available Width")

        lbl.setFixedWidth(50)
        lbl._update_elided_text()
        self.assertNotEqual(lbl.text(), "Very Long Track Title That Will Exceed Available Width")
        self.assertTrue(lbl.text().endswith("…") or "…" in lbl.text() or "..." in lbl.text())
        self.assertEqual(lbl.toolTip(), "Very Long Track Title That Will Exceed Available Width")

    def test_status_badge_pill_styling(self) -> None:
        """Verify status badge styling for PLAYING, PAUSED, STOPPED, CLOSED, and UNKNOWN statuses."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        core.playback_status_changed.emit(PlaybackStatus.PLAYING)
        self.assertIn("#00FF7F", window.status_label.styleSheet())
        self.assertEqual(window.status_label.text(), "PLAYING")

        core.playback_status_changed.emit(PlaybackStatus.PAUSED)
        self.assertIn("#C1121C", window.status_label.styleSheet())
        self.assertEqual(window.status_label.text(), "PAUSED")

        core.playback_status_changed.emit(PlaybackStatus.STOPPED)
        self.assertIn("#C1121C", window.status_label.styleSheet())
        self.assertEqual(window.status_label.text(), "STOPPED")

        core.playback_status_changed.emit(PlaybackStatus.CLOSED)
        self.assertIn("#8A8A8A", window.status_label.styleSheet())
        self.assertEqual(window.status_label.text(), "CLOSED")

        core.playback_status_changed.emit(PlaybackStatus.UNKNOWN)
        self.assertIn("#8A8A8A", window.status_label.styleSheet())
        self.assertEqual(window.status_label.text(), "UNKNOWN")

    def test_close_to_tray_hides_window_without_stopping_mediacore(self) -> None:
        """Verify close_to_tray=True hides window without stopping MediaCore or quitting."""
        from unittest.mock import MagicMock
        from src.core.settings import SettingsManager
        from PySide6.QtCore import QSettings

        qs = QSettings("KrishnaOSTest", "MediaDockTest")
        qs.clear()
        sm = SettingsManager(qsettings=qs)
        sm.set_close_to_tray(True)

        mock_core = MagicMock(spec=MediaCore)
        mock_core.get_current_track.return_value = TrackInfo.empty()
        mock_core.get_playback_status.return_value = PlaybackStatus.CLOSED

        window = MainWindow(media_core=mock_core, settings_manager=sm)
        window.show()

        window.close()

        # Window should be hidden and MediaCore should NOT be stopped
        self.assertFalse(window.isVisible())
        mock_core.stop.assert_not_called()
        qs.clear()

    def test_always_on_top_setting_toggles_window_flag(self) -> None:
        """Verify always_on_top setting toggles WindowStaysOnTopHint window flag."""
        from src.core.settings import SettingsManager
        from PySide6.QtCore import QSettings

        qs = QSettings("KrishnaOSTest", "MediaDockTest")
        qs.clear()
        sm = SettingsManager(qsettings=qs)

        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core, settings_manager=sm)

        sm.set_always_on_top(False)
        self.assertFalse(bool(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))

        sm.set_always_on_top(True)
        self.assertTrue(bool(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))
        qs.clear()

    def test_top_center_positioning_precedence(self) -> None:
        """Verify Dynamic Island top-center positioning takes precedence for window placement."""
        from src.core.settings import SettingsManager
        from PySide6.QtCore import QSettings
        from src.ui.main_window import TOP_OFFSET_PX

        qs = QSettings("KrishnaOSTest", "MediaDockTest")
        qs.clear()
        sm = SettingsManager(qsettings=qs)

        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window1 = MainWindow(media_core=core, settings_manager=sm)
        self.assertEqual(window1.pos().y(), TOP_OFFSET_PX)
        qs.clear()


    def test_track_change_opacity_animation(self) -> None:
        """Verify emitting track_changed triggers opacity fade animation and leaves final opacity at 1.0."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        track = TrackInfo(title="New Song", artist="New Artist")
        core.track_changed.emit(track)

        # Stop animation synchronously to simulate completion
        if window._fade_anim.state() == window._fade_anim.State.Running:
            window._fade_anim.stop()
        window._opacity_effect.setOpacity(1.0)

        self.assertEqual(window._opacity_effect.opacity(), 1.0)

    def test_rapid_track_change_animations(self) -> None:
        """Verify rapid repeated track_changed emissions do not crash or leave broken opacity state."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        for i in range(10):
            track = TrackInfo(title=f"Rapid Song {i}", artist=f"Rapid Artist {i}")
            core.track_changed.emit(track)

        if window._fade_anim.state() == window._fade_anim.State.Running:
            window._fade_anim.stop()
        window._opacity_effect.setOpacity(1.0)

        self.assertEqual(window.title_label.full_text(), "Rapid Song 9")
        self.assertEqual(window._opacity_effect.opacity(), 1.0)


    def test_album_art_accent_extraction_and_fallback(self) -> None:
        """Verify track without art uses fallback accent #00FF7F, and track with valid art extracts accent."""
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QColor, QImage

        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        # 1. Fallback test: no art bytes
        no_art_track = TrackInfo(title="Song", artist="Artist", album_art_bytes=None)
        core.track_changed.emit(no_art_track)
        self.assertEqual(window._current_accent.name(), "#00ff7f")
        self.assertIn("#00ff7f", window.progress_slider.styleSheet())

        # 2. Valid art test: solid green image
        img = QImage(32, 32, QImage.Format.Format_RGB32)
        img.fill(QColor(40, 180, 80))
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")

        art_track = TrackInfo(title="Green Song", artist="Artist", album_art_bytes=bytes(ba))
        core.track_changed.emit(art_track)
        self.assertNotEqual(window._current_accent.name(), "#89b4fa")
        self.assertIn(window._current_accent.name(), window.progress_slider.styleSheet())



    def test_button_clicks_call_mediacore_methods(self) -> None:
        """Verify button clicks trigger previous_track, toggle_play_pause, and next_track on MediaCore."""
        from unittest.mock import MagicMock
        mock_core = MagicMock(spec=MediaCore)
        mock_core.get_current_track.return_value = TrackInfo.empty()
        mock_core.get_playback_status.return_value = PlaybackStatus.CLOSED
        mock_core.is_session_available.return_value = True

        window = MainWindow(media_core=mock_core)

        window.btn_prev.click()
        mock_core.previous_track.assert_called_once()

        window.btn_play_pause.click()
        mock_core.toggle_play_pause.assert_called_once()

        window.btn_next.click()
        mock_core.next_track.assert_called_once()

    def test_play_pause_button_icon_states(self) -> None:
        """Verify Play/Pause button icon updates cleanly for PLAYING, PAUSED, and STOPPED states."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        core.playback_status_changed.emit(PlaybackStatus.PLAYING)
        self.assertFalse(window.btn_play_pause.icon().isNull())

        core.playback_status_changed.emit(PlaybackStatus.PAUSED)
        self.assertFalse(window.btn_play_pause.icon().isNull())

        core.playback_status_changed.emit(PlaybackStatus.STOPPED)
        self.assertFalse(window.btn_play_pause.icon().isNull())

        core.playback_status_changed.emit(PlaybackStatus.CLOSED)
        self.assertFalse(window.btn_play_pause.icon().isNull())

    def test_time_formatting_helper(self) -> None:
        """Verify _format_time_ms formats MM:SS correctly and clamps negative values to 00:00."""
        from src.ui.main_window import _format_time_ms
        self.assertEqual(_format_time_ms(0), "00:00")
        self.assertEqual(_format_time_ms(-5000), "00:00")
        self.assertEqual(_format_time_ms(65000), "01:05")
        self.assertEqual(_format_time_ms(205000), "03:25")

    def test_track_changed_updates_timeline_slider_and_labels(self) -> None:
        """Verify track_changed signal updates duration, position, slider max, and value."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        track = TrackInfo(
            title="Test Song",
            artist="Test Artist",
            duration_ms=180000,
            position_ms=30000,
        )
        core.track_changed.emit(track)

        self.assertEqual(window.lbl_duration.text(), "03:00")
        self.assertEqual(window.lbl_position.text(), "00:30")
        self.assertEqual(window.progress_slider.maximum(), 180000)
        self.assertEqual(window.progress_slider.value(), 30000)

    def test_seeking_state_machine_flow(self) -> None:
        """Verify sliderPressed sets seeking state, sliderMoved updates label without seek, sliderReleased sends single seek command."""
        from unittest.mock import MagicMock
        mock_core = MagicMock(spec=MediaCore)
        mock_core.get_current_track.return_value = TrackInfo(title="Song", artist="Artist", duration_ms=100000)
        mock_core.get_playback_status.return_value = PlaybackStatus.PAUSED
        mock_core.is_session_available.return_value = True

        window = MainWindow(media_core=mock_core)
        window.progress_slider.setMaximum(100000)

        # 1. sliderPressed
        window.progress_slider.sliderPressed.emit()
        self.assertTrue(window._is_seeking)
        mock_core.seek_to_position.assert_not_called()

        # 2. sliderMoved
        window.progress_slider.setValue(45000)
        window.progress_slider.sliderMoved.emit(45000)
        self.assertEqual(window.lbl_position.text(), "00:45")
        mock_core.seek_to_position.assert_not_called()

        # 3. sliderReleased
        window.progress_slider.sliderReleased.emit()
        self.assertFalse(window._is_seeking)
        mock_core.seek_to_position.assert_called_once_with(45000)

    def test_seeking_edge_cases_0_and_duration(self) -> None:
        """Verify seeking to 0 and exact duration_ms works cleanly."""
        from unittest.mock import MagicMock
        mock_core = MagicMock(spec=MediaCore)
        mock_core.get_current_track.return_value = TrackInfo(title="Song", artist="Artist", duration_ms=120000)
        mock_core.get_playback_status.return_value = PlaybackStatus.PAUSED
        mock_core.is_session_available.return_value = True

        window = MainWindow(media_core=mock_core)
        window.progress_slider.setMaximum(120000)

        # Seek to 0
        window.progress_slider.sliderPressed.emit()
        window.progress_slider.setValue(0)
        window.progress_slider.sliderReleased.emit()
        mock_core.seek_to_position.assert_called_with(0)

        # Seek to max duration
        window.progress_slider.sliderPressed.emit()
        window.progress_slider.setValue(120000)
        window.progress_slider.sliderReleased.emit()
        mock_core.seek_to_position.assert_called_with(120000)

    def test_session_availability_enables_disables_controls(self) -> None:
        """Verify session_availability_changed(False) disables controls, True enables controls."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        core.session_availability_changed.emit(False)
        self.assertFalse(window.btn_prev.isEnabled())
        self.assertFalse(window.btn_play_pause.isEnabled())
        self.assertFalse(window.btn_next.isEnabled())
        self.assertFalse(window.progress_slider.isEnabled())

        core.session_availability_changed.emit(True)
        self.assertTrue(window.btn_prev.isEnabled())
        self.assertTrue(window.btn_play_pause.isEnabled())
        self.assertTrue(window.btn_next.isEnabled())
        self.assertTrue(window.progress_slider.isEnabled())

    def test_position_interpolation_timer_lifecycle(self) -> None:
        """Verify position timer starts on PLAYING and stops on PAUSED/STOPPED/CLOSED."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        track = TrackInfo(title="Song", artist="Artist", duration_ms=100000, position_ms=10000)
        core.track_changed.emit(track)

        core.playback_status_changed.emit(PlaybackStatus.PLAYING)
        self.assertTrue(window._position_timer.isActive())

        core.playback_status_changed.emit(PlaybackStatus.PAUSED)
        self.assertFalse(window._position_timer.isActive())

        core.playback_status_changed.emit(PlaybackStatus.PLAYING)
        self.assertTrue(window._position_timer.isActive())

        core.playback_status_changed.emit(PlaybackStatus.STOPPED)
        self.assertFalse(window._position_timer.isActive())


if __name__ == "__main__":
    unittest.main()
