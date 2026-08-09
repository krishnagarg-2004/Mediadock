"""Unit tests for src/ui/hotkeys.py GlobalHotkeyManager and native event filter."""

import sys
import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QCoreApplication

from src.ui.hotkeys import (
    GlobalHotkeyManager,
    HotkeyNativeEventFilter,
    HOTKEY_ID_SHOW_HIDE,
    HOTKEY_ID_PLAY_PAUSE,
    WM_HOTKEY,
)


class TestGlobalHotkeyManager(unittest.TestCase):
    """Test suite for GlobalHotkeyManager registration, signal emission, and lifecycle."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure QCoreApplication instance exists for Qt signal/event testing."""
        cls.app = QCoreApplication.instance()
        if cls.app is None:
            cls.app = QCoreApplication(sys.argv)

    def setUp(self) -> None:
        """Create fresh GlobalHotkeyManager for each test."""
        self.manager = GlobalHotkeyManager()

    def tearDown(self) -> None:
        """Ensure manager is stopped after each test."""
        self.manager.stop()

    # --- Native Event Filter & Signal Decoding Tests ---

    def test_native_event_filter_decodes_show_hide(self) -> None:
        """Verify native event filter emits show_hide_requested on WM_HOTKEY ID 1."""
        signal_received = False

        def on_signal() -> None:
            nonlocal signal_received
            signal_received = True

        self.manager.show_hide_requested.connect(on_signal)
        filter_inst = HotkeyNativeEventFilter(self.manager._on_hotkey_triggered)

        # Trigger callback with ID 1
        filter_inst._callback(HOTKEY_ID_SHOW_HIDE)
        self.assertTrue(signal_received)

    def test_native_event_filter_decodes_play_pause(self) -> None:
        """Verify native event filter emits play_pause_requested on WM_HOTKEY ID 2."""
        signal_received = False

        def on_signal() -> None:
            nonlocal signal_received
            signal_received = True

        self.manager.play_pause_requested.connect(on_signal)
        filter_inst = HotkeyNativeEventFilter(self.manager._on_hotkey_triggered)

        # Trigger callback with ID 2
        filter_inst._callback(HOTKEY_ID_PLAY_PAUSE)
        self.assertTrue(signal_received)

    def test_native_event_filter_direct_msg_decoding(self) -> None:
        """Verify nativeEventFilter parses Win32 MSG pointer and routes show_hide and play_pause."""
        import ctypes
        from src.ui.hotkeys import MSG, IS_WINDOWS

        if not IS_WINDOWS:
            return

        show_hide_received = False
        play_pause_received = False

        def on_show_hide() -> None:
            nonlocal show_hide_received
            show_hide_received = True

        def on_play_pause() -> None:
            nonlocal play_pause_received
            play_pause_received = True

        self.manager.show_hide_requested.connect(on_show_hide)
        self.manager.play_pause_requested.connect(on_play_pause)
        filter_inst = HotkeyNativeEventFilter(self.manager._on_hotkey_triggered)

        # 1. Test WM_HOTKEY (0x0312) with wParam = 1 (Show/Hide)
        msg_show_hide = MSG(message=WM_HOTKEY, wParam=HOTKEY_ID_SHOW_HIDE)
        msg_ptr_1 = ctypes.addressof(msg_show_hide)
        handled_1, res_1 = filter_inst.nativeEventFilter(b"windows_generic_MSG", msg_ptr_1)
        self.assertTrue(handled_1)
        self.assertEqual(res_1, 0)
        self.assertTrue(show_hide_received)
        self.assertFalse(play_pause_received)

        # 2. Test WM_HOTKEY (0x0312) with wParam = 2 (Play/Pause)
        msg_play_pause = MSG(message=WM_HOTKEY, wParam=HOTKEY_ID_PLAY_PAUSE)
        msg_ptr_2 = ctypes.addressof(msg_play_pause)
        handled_2, res_2 = filter_inst.nativeEventFilter(b"windows_generic_MSG", msg_ptr_2)
        self.assertTrue(handled_2)
        self.assertEqual(res_2, 0)
        self.assertTrue(play_pause_received)

        # 3. Test non-WM_HOTKEY message (ignored)
        msg_other = MSG(message=0x0000, wParam=1)
        msg_ptr_3 = ctypes.addressof(msg_other)
        handled_3, res_3 = filter_inst.nativeEventFilter(b"windows_generic_MSG", msg_ptr_3)
        self.assertFalse(handled_3)


    # --- Win32 Registration & Failure Tests ---

    @patch("ctypes.windll")
    def test_successful_hotkey_registration(self, mock_windll: MagicMock) -> None:
        """Verify start registers both global hotkeys when RegisterHotKey succeeds."""
        mock_user32 = MagicMock()
        mock_user32.RegisterHotKey.return_value = 1
        mock_windll.user32 = mock_user32

        with patch("src.ui.hotkeys.IS_WINDOWS", True):
            res = self.manager.start()
            self.assertTrue(res)
            self.assertTrue(self.manager.is_started)
            self.assertTrue(self.manager.is_registered(HOTKEY_ID_SHOW_HIDE))
            self.assertTrue(self.manager.is_registered(HOTKEY_ID_PLAY_PAUSE))
            self.assertEqual(mock_user32.RegisterHotKey.call_count, 2)

    @patch("ctypes.windll")
    def test_registration_failure_handling(self, mock_windll: MagicMock) -> None:
        """Verify start handles complete registration failure non-fatally."""
        mock_user32 = MagicMock()
        mock_user32.RegisterHotKey.return_value = 0
        mock_windll.user32 = mock_user32

        with patch("src.ui.hotkeys.IS_WINDOWS", True):
            res = self.manager.start()
            self.assertFalse(res)
            self.assertTrue(self.manager.is_started)
            self.assertFalse(self.manager.is_registered(HOTKEY_ID_SHOW_HIDE))
            self.assertFalse(self.manager.is_registered(HOTKEY_ID_PLAY_PAUSE))

    @patch("ctypes.windll")
    def test_partial_registration_handling(self, mock_windll: MagicMock) -> None:
        """Verify start preserves successfully registered hotkeys if one fails."""
        mock_user32 = MagicMock()
        # Return 1 for ID 1 (show/hide), 0 for ID 2 (play/pause)
        mock_user32.RegisterHotKey.side_effect = [1, 0]
        mock_windll.user32 = mock_user32

        with patch("src.ui.hotkeys.IS_WINDOWS", True):
            res = self.manager.start()
            self.assertTrue(res)
            self.assertTrue(self.manager.is_registered(HOTKEY_ID_SHOW_HIDE))
            self.assertFalse(self.manager.is_registered(HOTKEY_ID_PLAY_PAUSE))

    # --- Unregistration & Lifecycle Tests ---

    @patch("ctypes.windll")
    def test_stop_unregisters_hotkeys_and_resets_state(self, mock_windll: MagicMock) -> None:
        """Verify stop calls UnregisterHotKey for active IDs and clears internal state."""
        mock_user32 = MagicMock()
        mock_user32.RegisterHotKey.return_value = 1
        mock_user32.UnregisterHotKey.return_value = 1
        mock_windll.user32 = mock_user32

        with patch("src.ui.hotkeys.IS_WINDOWS", True):
            self.manager.start()
            self.assertTrue(self.manager.is_started)

            self.manager.stop()
            self.assertFalse(self.manager.is_started)
            self.assertFalse(self.manager.is_registered(HOTKEY_ID_SHOW_HIDE))
            self.assertFalse(self.manager.is_registered(HOTKEY_ID_PLAY_PAUSE))
            self.assertEqual(mock_user32.UnregisterHotKey.call_count, 2)

    @patch("ctypes.windll")
    def test_repeated_stop_calls_are_safe(self, mock_windll: MagicMock) -> None:
        """Verify calling stop multiple times consecutively is completely safe."""
        mock_user32 = MagicMock()
        mock_user32.RegisterHotKey.return_value = 1
        mock_user32.UnregisterHotKey.return_value = 1
        mock_windll.user32 = mock_user32

        with patch("src.ui.hotkeys.IS_WINDOWS", True):
            self.manager.start()
            self.manager.stop()
            # Repeated calls
            self.manager.stop()
            self.manager.stop()

            self.assertFalse(self.manager.is_started)

    def test_non_windows_platform_graceful_fallback(self) -> None:
        """Verify non-Windows platform returns False without accessing user32."""
        with patch("src.ui.hotkeys.IS_WINDOWS", False):
            res = self.manager.start()
            self.assertFalse(res)
            self.assertFalse(self.manager.is_started)


if __name__ == "__main__":
    unittest.main()
