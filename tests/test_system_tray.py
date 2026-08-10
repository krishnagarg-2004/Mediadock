"""Unit tests for src/ui/system_tray.py SystemTrayIcon component."""

import sys
import unittest
from unittest.mock import MagicMock
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from src.core.models import TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider
from src.core.media_core import MediaCore
from src.ui.system_tray import SystemTrayIcon, create_tray_icon_pixmap


class DummyProvider(BaseMediaProvider):
    """Dummy media provider double for system tray integration tests."""

    def __init__(self) -> None:
        self.current_track = TrackInfo(title="Initial Track", artist="Initial Artist")
        self.current_status = PlaybackStatus.PAUSED
        self.session_available = True
        self.track_cb = None
        self.status_cb = None
        self.session_cb = None

    def get_current_track(self) -> TrackInfo:
        return self.current_track

    def get_playback_status(self) -> PlaybackStatus:
        return self.current_status

    def is_session_available(self) -> bool:
        return self.session_available

    def start_listening(self) -> None: pass
    def stop_listening(self) -> None: pass
    def set_on_track_changed(self, cb) -> None: self.track_cb = cb
    def set_on_status_changed(self, cb) -> None: self.status_cb = cb
    def set_on_session_availability_changed(self, cb) -> None: self.session_cb = cb

    def play(self) -> bool: return True
    def pause(self) -> bool: return True
    def toggle_play_pause(self) -> bool: return True
    def next_track(self) -> bool: return True
    def previous_track(self) -> bool: return True
    def seek_to_position(self, pos_ms: int) -> bool: return True


class TestSystemTrayIcon(unittest.TestCase):
    """Test suite for SystemTrayIcon initialization, context menu, and dynamic tooltips."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure QApplication instance exists for GUI/tray testing."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_create_tray_icon_pixmap(self) -> None:
        """Verify vector tray icon pixmap generates cleanly with specified size."""
        pixmap = create_tray_icon_pixmap(32)
        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 32)
        self.assertEqual(pixmap.height(), 32)

    def test_system_tray_instantiation(self) -> None:
        """Verify SystemTrayIcon initializes with context menu and default tooltip."""
        tray = SystemTrayIcon()
        self.assertIsNotNone(tray.contextMenu())
        self.assertEqual(tray.toolTip(), "MediaDock - No Media Playing")

    def test_menu_actions_exist(self) -> None:
        """Verify context menu contains Show/Hide, Settings, and Exit actions."""
        tray = SystemTrayIcon()
        menu = tray.contextMenu()
        actions = menu.actions()

        action_labels = [a.text() for a in actions if not a.isSeparator()]
        self.assertIn("Show MediaDock", action_labels)
        self.assertIn("Settings...", action_labels)
        self.assertIn("Exit MediaDock", action_labels)

    def test_update_menu_state(self) -> None:
        """Verify update_menu_state toggles action text between Show and Hide."""
        tray = SystemTrayIcon()
        tray.update_menu_state(True)
        self.assertEqual(tray.action_show_hide.text(), "Hide MediaDock")

        tray.update_menu_state(False)
        self.assertEqual(tray.action_show_hide.text(), "Show MediaDock")

    def test_menu_action_signals(self) -> None:
        """Verify triggering menu actions emits show_hide, settings, and exit signals."""
        tray = SystemTrayIcon()

        mock_show_hide = MagicMock()
        mock_settings = MagicMock()
        mock_exit = MagicMock()

        tray.show_hide_requested.connect(mock_show_hide)
        tray.settings_requested.connect(mock_settings)
        tray.exit_requested.connect(mock_exit)

        tray.action_show_hide.trigger()
        mock_show_hide.assert_called_once()

        tray.action_settings.trigger()
        mock_settings.assert_called_once()

        tray.action_exit.trigger()
        mock_exit.assert_called_once()

    def test_tray_activation_signals(self) -> None:
        """Verify left click (Trigger) emits show_hide_requested and DoubleClick emits show_requested."""
        tray = SystemTrayIcon()
        mock_show_hide = MagicMock()
        mock_show = MagicMock()
        tray.show_hide_requested.connect(mock_show_hide)
        tray.show_requested.connect(mock_show)

        tray._on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
        mock_show_hide.assert_called_once()
        mock_show.assert_not_called()

        mock_show_hide.reset_mock()
        tray._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
        mock_show_hide.assert_not_called()
        mock_show.assert_called_once()


    def test_tooltip_formatting_scenarios(self) -> None:
        """Verify tooltip formats playing media, paused media, and closed media correctly."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        tray = SystemTrayIcon(media_core=core)

        # 1. Playing media
        playing_track = TrackInfo(title="Die With A Smile", artist="Lady Gaga & Bruno Mars")
        provider.current_track = playing_track
        provider.current_status = PlaybackStatus.PLAYING
        core.track_changed.emit(playing_track)
        core.playback_status_changed.emit(PlaybackStatus.PLAYING)

        self.assertEqual(tray.toolTip(), "MediaDock - Die With A Smile by Lady Gaga & Bruno Mars [PLAYING]")

        # 2. Paused media
        provider.current_status = PlaybackStatus.PAUSED
        core.playback_status_changed.emit(PlaybackStatus.PAUSED)
        self.assertEqual(tray.toolTip(), "MediaDock - Die With A Smile by Lady Gaga & Bruno Mars [PAUSED]")

        # 3. Session unavailable / CLOSED
        core.session_availability_changed.emit(False)
        self.assertEqual(tray.toolTip(), "MediaDock - No Media Playing")

    def test_compact_mode_action_and_signal(self) -> None:
        """Verify context menu contains checkable Compact Mode action that emits compact_mode_requested."""
        tray = SystemTrayIcon()
        self.assertIsNotNone(tray.action_compact_mode)
        self.assertTrue(tray.action_compact_mode.isCheckable())

        mock_compact_cb = MagicMock()
        tray.compact_mode_requested.connect(mock_compact_cb)

        tray.action_compact_mode.trigger()
        mock_compact_cb.assert_called_once_with(True)

    def test_set_compact_mode_checked(self) -> None:
        """Verify set_compact_mode_checked updates action check state."""
        tray = SystemTrayIcon()
        tray.set_compact_mode_checked(True)
        self.assertTrue(tray.action_compact_mode.isChecked())

        tray.set_compact_mode_checked(False)
        self.assertFalse(tray.action_compact_mode.isChecked())

    def test_hide_tray_icon_cleanup(self) -> None:
        """Verify hide_tray_icon hides the system tray icon."""
        tray = SystemTrayIcon()
        tray.show()
        tray.hide_tray_icon()
        self.assertFalse(tray.isVisible())


if __name__ == "__main__":
    unittest.main()
