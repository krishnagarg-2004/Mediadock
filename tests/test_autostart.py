"""Unit tests for src/utils/autostart.py AutostartManager and registry integration."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from src.utils.autostart import AutostartManager
from src.core.settings import SettingsManager
from src.ui.settings_dialog import SettingsDialog


class TestAutostartManager(unittest.TestCase):
    """Test suite for AutostartManager registry operations, startup command selection, and settings binding."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure QApplication instance exists for GUI testing."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self) -> None:
        """Create isolated temporary INI QSettings store for each test."""
        import tempfile
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        self.tmp_file.close()
        self.qs = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        self.settings = SettingsManager(qsettings=self.qs)

    def tearDown(self) -> None:
        """Clean up isolated temporary INI file after each test."""
        import os
        if hasattr(self, "tmp_file") and os.path.exists(self.tmp_file.name):
            try:
                os.unlink(self.tmp_file.name)
            except OSError:
                pass



    # --- AutostartManager Direct Unit Tests ---

    @patch("src.utils.autostart.winreg")
    def test_is_autostart_enabled_true(self, mock_winreg: MagicMock) -> None:
        """Verify is_autostart_enabled returns True when registry value exists."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ('"C:\\path\\MediaDock.exe" --minimized', mock_winreg.REG_SZ)

        self.assertTrue(AutostartManager.is_autostart_enabled())
        mock_winreg.OpenKey.assert_called_once()
        mock_winreg.QueryValueEx.assert_called_once_with(mock_key, "MediaDock")

    @patch("src.utils.autostart.winreg")
    def test_is_autostart_enabled_false_on_missing_key(self, mock_winreg: MagicMock) -> None:
        """Verify is_autostart_enabled returns False when registry key is missing."""
        mock_winreg.OpenKey.side_effect = FileNotFoundError("Key not found")
        self.assertFalse(AutostartManager.is_autostart_enabled())

    @patch("src.utils.autostart.winreg")
    def test_enable_autostart_success(self, mock_winreg: MagicMock) -> None:
        """Verify enable_autostart writes startup command to registry and returns True."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        success = AutostartManager.enable_autostart()
        self.assertTrue(success)
        mock_winreg.SetValueEx.assert_called_once()
        args = mock_winreg.SetValueEx.call_args[0]
        self.assertEqual(args[1], "MediaDock")
        self.assertIn("--minimized", args[4])

    @patch("src.utils.autostart.winreg")
    def test_enable_autostart_failure_handles_oserror(self, mock_winreg: MagicMock) -> None:
        """Verify enable_autostart handles OSError gracefully and returns False."""
        mock_winreg.OpenKey.side_effect = OSError("Permission denied")
        success = AutostartManager.enable_autostart()
        self.assertFalse(success)

    @patch("src.utils.autostart.winreg")
    def test_disable_autostart_success(self, mock_winreg: MagicMock) -> None:
        """Verify disable_autostart removes registry key and returns True."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        success = AutostartManager.disable_autostart()
        self.assertTrue(success)
        mock_winreg.DeleteValue.assert_called_once_with(mock_key, "MediaDock")

    @patch("src.utils.autostart.winreg")
    def test_disable_autostart_missing_key_returns_true(self, mock_winreg: MagicMock) -> None:
        """Verify disable_autostart handles FileNotFoundError cleanly (already disabled)."""
        mock_winreg.OpenKey.side_effect = FileNotFoundError()
        self.assertTrue(AutostartManager.disable_autostart())

    def test_startup_command_development_vs_packaged(self) -> None:
        """Verify get_startup_command formatting in development vs frozen execution."""
        # 1. Development environment (resists arbitrary sys.argv[0] paths)
        with patch.object(sys, "argv", ["C:\\Windows\\System32\\unrelated.py"]):
            cmd_dev = AutostartManager.get_startup_command()
            self.assertIn(sys.executable, cmd_dev)
            self.assertIn("main.py", cmd_dev)
            self.assertIn("--minimized", cmd_dev)

        # 2. PyInstaller packaged environment simulation
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", "C:\\Program Files\\MediaDock\\MediaDock.exe"):
            cmd_pkg = AutostartManager.get_startup_command()
            self.assertEqual(cmd_pkg, '"C:\\Program Files\\MediaDock\\MediaDock.exe" --minimized')

    @patch("src.utils.autostart.winreg")
    def test_reconcile_restores_registry_when_enabled(self, mock_winreg: MagicMock) -> None:
        """Verify AutostartManager.reconcile(True) ensures the Windows Run registry key is populated."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        self.assertTrue(AutostartManager.reconcile(True))
        mock_winreg.SetValueEx.assert_called_once()

        mock_winreg.reset_mock()
        self.assertTrue(AutostartManager.reconcile(False))
        mock_winreg.SetValueEx.assert_not_called()

    # --- SettingsManager Integration Tests ---

    def test_settings_manager_autostart_default(self) -> None:
        """Verify general/autostart_windows defaults to False."""
        self.assertFalse(self.settings.get_autostart_windows())

    @patch("src.utils.autostart.winreg")
    def test_settings_manager_set_autostart_success(self, mock_winreg: MagicMock) -> None:
        """Verify set_autostart_windows updates QSettings when registry operation succeeds."""
        mock_winreg.OpenKey.side_effect = None
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        res = self.settings.set_autostart_windows(True)
        self.assertTrue(res)
        self.assertTrue(self.settings.get_autostart_windows())



    @patch("src.utils.autostart.winreg")
    def test_settings_manager_set_autostart_failure_does_not_persist(self, mock_winreg: MagicMock) -> None:
        """Verify set_autostart_windows returns False if registry operation fails while recording preference."""
        mock_winreg.OpenKey.side_effect = OSError("Registry write error")

        res = self.settings.set_autostart_windows(True)
        self.assertFalse(res)
        self.assertTrue(self.settings.get_autostart_windows())

    # --- SettingsDialog UI Binding Tests ---

    @patch("src.utils.autostart.winreg")
    def test_settings_dialog_autostart_checkbox_binding(self, mock_winreg: MagicMock) -> None:
        """Verify SettingsDialog loads and saves autostart preference."""
        mock_winreg.OpenKey.side_effect = None
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        # Initial load (False)
        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertFalse(dlg.chk_autostart_windows.isChecked())

        # Toggle to True and save
        dlg.chk_autostart_windows.setChecked(True)
        dlg.save_settings()

        self.assertTrue(self.settings.get_autostart_windows())

    @patch("src.utils.autostart.winreg")
    def test_settings_dialog_cancel_discards_autostart(self, mock_winreg: MagicMock) -> None:
        """Verify Cancel in SettingsDialog discards autostart checkbox modification."""
        mock_winreg.OpenKey.side_effect = None
        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.chk_autostart_windows.setChecked(True)
        dlg.reject()

        self.assertFalse(self.settings.get_autostart_windows())



if __name__ == "__main__":
    unittest.main()
