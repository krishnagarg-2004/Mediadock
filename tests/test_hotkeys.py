"""Unit tests for src/ui/hotkeys.py GlobalHotkeyManager, parse_key_sequence, and SettingsDialog hotkey integration."""

import sys
import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QCoreApplication

from src.core.settings import SettingsManager
from src.ui.settings_dialog import SettingsDialog
from src.ui.hotkeys import (
    GlobalHotkeyManager,
    HotkeyNativeEventFilter,
    parse_key_sequence,
    HOTKEY_ID_SHOW_HIDE,
    HOTKEY_ID_PLAY_PAUSE,
    WM_HOTKEY,
    MOD_CONTROL,
    MOD_ALT,
    MOD_SHIFT,
    MOD_WIN,
    VK_M,
    VK_SPACE,
)

# Ensure QCoreApplication instance exists for Qt testing
_app = QCoreApplication.instance() or QCoreApplication(sys.argv)


class TestHotkeyParser(unittest.TestCase):
    """Test suite for Qt-style key sequence parsing to Win32 modifier bitmasks and virtual keys."""

    def test_parse_valid_sequences(self) -> None:
        """Verify parsing standard valid hotkey sequences."""
        # Ctrl+Alt+M
        mods, vk = parse_key_sequence("Ctrl+Alt+M")
        self.assertEqual(mods, MOD_CONTROL | MOD_ALT)
        self.assertEqual(vk, VK_M)

        # Ctrl+Alt+Space
        mods, vk = parse_key_sequence("Ctrl+Alt+Space")
        self.assertEqual(mods, MOD_CONTROL | MOD_ALT)
        self.assertEqual(vk, VK_SPACE)

        # Ctrl+Shift+P
        mods, vk = parse_key_sequence("Ctrl+Shift+P")
        self.assertEqual(mods, MOD_CONTROL | MOD_SHIFT)
        self.assertEqual(vk, ord("P"))

        # Win+Space
        mods, vk = parse_key_sequence("Win+Space")
        self.assertEqual(mods, MOD_WIN)
        self.assertEqual(vk, VK_SPACE)

        # Alt+F5
        mods, vk = parse_key_sequence("Alt+F5")
        self.assertEqual(mods, MOD_ALT)
        self.assertEqual(vk, 0x74)  # F5 VK

        # Ctrl+1
        mods, vk = parse_key_sequence("Ctrl+1")
        self.assertEqual(mods, MOD_CONTROL)
        self.assertEqual(vk, ord("1"))

    def test_parse_invalid_sequences(self) -> None:
        """Verify parse_key_sequence rejects invalid or malformed sequences cleanly."""
        # Missing modifier
        with self.assertRaises(ValueError):
            parse_key_sequence("M")

        with self.assertRaises(ValueError):
            parse_key_sequence("Space")

        # Empty or non-string
        with self.assertRaises(ValueError):
            parse_key_sequence("")

        # Unknown key token
        with self.assertRaises(ValueError):
            parse_key_sequence("Ctrl+InvalidKeyName")

        # Multiple main keys
        with self.assertRaises(ValueError):
            parse_key_sequence("Ctrl+A+B")


class TestGlobalHotkeyManager(unittest.TestCase):
    """Test suite for GlobalHotkeyManager registration, signal emission, and rollback lifecycle."""

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

    # --- Win32 Registration & Rebind Rollback Tests ---

    @patch("ctypes.windll")
    def test_successful_hotkey_registration(self, mock_windll: MagicMock) -> None:
        """Verify start registers both configured global hotkeys when RegisterHotKey succeeds."""
        mock_user32 = MagicMock()
        mock_user32.RegisterHotKey.return_value = 1
        mock_windll.user32 = mock_user32

        with patch("src.ui.hotkeys.IS_WINDOWS", True):
            res = self.manager.start("Ctrl+Alt+M", "Ctrl+Alt+Space")
            self.assertTrue(res)
            self.assertTrue(self.manager.is_started)
            self.assertTrue(self.manager.is_registered(HOTKEY_ID_SHOW_HIDE))
            self.assertTrue(self.manager.is_registered(HOTKEY_ID_PLAY_PAUSE))
            self.assertEqual(mock_user32.RegisterHotKey.call_count, 2)

    @patch("ctypes.windll")
    def test_successful_rebind_hotkeys(self, mock_windll: MagicMock) -> None:
        """Verify rebind_hotkeys updates shortcuts when registration succeeds."""
        mock_user32 = MagicMock()
        mock_user32.RegisterHotKey.return_value = 1
        mock_user32.UnregisterHotKey.return_value = 1
        mock_windll.user32 = mock_user32

        with patch("src.ui.hotkeys.IS_WINDOWS", True):
            self.manager.start("Ctrl+Alt+M", "Ctrl+Alt+Space")
            res = self.manager.rebind_hotkeys("Ctrl+Shift+H", "Ctrl+Shift+P")
            self.assertTrue(res)
            self.assertEqual(self.manager.get_show_hide_sequence(), "Ctrl+Shift+H")
            self.assertEqual(self.manager.get_play_pause_sequence(), "Ctrl+Shift+P")

    @patch("ctypes.windll")
    def test_rebind_duplicate_shortcuts_rejected(self, mock_windll: MagicMock) -> None:
        """Verify rebind_hotkeys rejects duplicate shortcuts for both actions."""
        mock_user32 = MagicMock()
        mock_user32.RegisterHotKey.return_value = 1
        mock_windll.user32 = mock_user32

        with patch("src.ui.hotkeys.IS_WINDOWS", True):
            self.manager.start("Ctrl+Alt+M", "Ctrl+Alt+Space")
            res = self.manager.rebind_hotkeys("Ctrl+Shift+X", "Ctrl+Shift+X")
            self.assertFalse(res)
            self.assertEqual(self.manager.get_show_hide_sequence(), "Ctrl+Alt+M")
            self.assertEqual(self.manager.get_play_pause_sequence(), "Ctrl+Alt+Space")

    @patch("ctypes.windll")
    def test_rebind_failure_triggers_rollback(self, mock_windll: MagicMock) -> None:
        """Verify rebind_hotkeys rolls back to previous shortcuts if Win32 RegisterHotKey fails."""
        mock_user32 = MagicMock()
        # Initial start: return 1 (success)
        # Rebind attempt: return 0 (failure)
        # Rollback re-register: return 1 (success)
        mock_user32.RegisterHotKey.side_effect = [1, 1, 0, 1, 1]
        mock_user32.UnregisterHotKey.return_value = 1
        mock_windll.user32 = mock_user32

        with patch("src.ui.hotkeys.IS_WINDOWS", True):
            self.manager.start("Ctrl+Alt+M", "Ctrl+Alt+Space")

            res = self.manager.rebind_hotkeys("Ctrl+Alt+X", "Ctrl+Alt+Y")
            self.assertFalse(res)
            # Must retain original working shortcuts
            self.assertEqual(self.manager.get_show_hide_sequence(), "Ctrl+Alt+M")
            self.assertEqual(self.manager.get_play_pause_sequence(), "Ctrl+Alt+Space")

    def test_non_windows_platform_graceful_fallback(self) -> None:
        """Verify non-Windows platform returns False without accessing user32."""
        with patch("src.ui.hotkeys.IS_WINDOWS", False):
            res = self.manager.start()
            self.assertFalse(res)
            self.assertFalse(self.manager.is_started)


class TestHotkeySettingsIntegration(unittest.TestCase):
    """Test suite for SettingsManager hotkey persistence and SettingsDialog integration."""

    def test_settings_manager_hotkey_defaults_and_accessors(self) -> None:
        """Verify SettingsManager provides default hotkey values and accessors."""
        sm = SettingsManager()
        sm.clear()

        self.assertEqual(sm.get_hotkey_show_hide(), "Ctrl+Alt+S")
        self.assertEqual(sm.get_hotkey_play_pause(), "Ctrl+Alt+Space")

        sm.set_hotkey_show_hide("Ctrl+Shift+S")
        sm.set_hotkey_play_pause("Ctrl+Shift+P")

        self.assertEqual(sm.get_hotkey_show_hide(), "Ctrl+Shift+S")
        self.assertEqual(sm.get_hotkey_play_pause(), "Ctrl+Shift+P")

    @patch("ctypes.windll")
    def test_settings_dialog_failed_rebind_shows_error_and_prevents_persistence(
        self, mock_windll: MagicMock
    ) -> None:
        """Verify SettingsDialog displays error and avoids persisting broken hotkey settings on failed rebind."""
        mock_user32 = MagicMock()
        mock_user32.RegisterHotKey.return_value = 0
        mock_windll.user32 = mock_user32

        sm = SettingsManager()
        sm.clear()
        hk_manager = GlobalHotkeyManager()

        dialog = SettingsDialog(settings_manager=sm, hotkey_manager=hk_manager)
        dialog.txt_hotkey_show_hide.setText("InvalidNoModifier")
        dialog.txt_hotkey_play_pause.setText("Ctrl+Alt+Space")

        # Save should fail validation
        dialog.save_settings()
        self.assertFalse(dialog.lbl_error.isHidden())
        self.assertEqual(sm.get_hotkey_show_hide(), "Ctrl+Alt+S")



if __name__ == "__main__":
    unittest.main()
