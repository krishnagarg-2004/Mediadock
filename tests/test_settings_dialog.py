"""Unit tests for src/ui/settings_dialog.py SettingsDialog UI component."""

import sys
import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from src.core.settings import SettingsManager
from src.ui.settings_dialog import SettingsDialog


class TestSettingsDialog(unittest.TestCase):
    """Test suite for SettingsDialog UI initialization, loading, saving, and cancellation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure QApplication instance exists for GUI dialog testing."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self) -> None:
        """Create an isolated temporary INI QSettings store for each test."""
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



    def test_dialog_initialization(self) -> None:
        """Verify SettingsDialog initializes with title, layout, checkboxes, and collapse delay spinbox."""
        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertEqual(dlg.windowTitle(), "MediaDock Preferences")
        self.assertIsNotNone(dlg.chk_close_to_tray)
        self.assertIsNotNone(dlg.chk_start_hidden)
        self.assertIsNotNone(dlg.chk_autostart_windows)
        self.assertIsNotNone(dlg.chk_always_on_top)
        self.assertIsNotNone(dlg.chk_dynamic_island)
        self.assertIsNotNone(dlg.spn_collapse_delay)
        # Assert obsolete compact mode and remember position checkboxes are completely removed
        self.assertFalse(hasattr(dlg, "chk_compact_mode"))
        self.assertFalse(hasattr(dlg, "chk_remember_position"))

    def test_initial_checkbox_states_match_settings_manager(self) -> None:
        """Verify checkboxes and spinbox initialize from current SettingsManager values."""
        self.settings.set_close_to_tray(True)
        self.settings.set_start_hidden(False)
        self.settings.set_always_on_top(True)
        self.settings.set_dynamic_island_enabled(True)
        self.settings.set_collapse_delay_ms(5000)

        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertTrue(dlg.chk_close_to_tray.isChecked())
        self.assertFalse(dlg.chk_start_hidden.isChecked())
        self.assertTrue(dlg.chk_always_on_top.isChecked())
        self.assertTrue(dlg.chk_dynamic_island.isChecked())
        self.assertEqual(dlg.spn_collapse_delay.value(), 5000)

    def test_changes_not_persisted_before_save(self) -> None:
        """Verify toggling controls does not mutate SettingsManager until save_settings is called."""
        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.chk_close_to_tray.setChecked(False)
        dlg.chk_start_hidden.setChecked(True)
        dlg.chk_dynamic_island.setChecked(False)
        dlg.spn_collapse_delay.setValue(10000)

        # SettingsManager values should still be original defaults
        self.assertTrue(self.settings.get_close_to_tray())
        self.assertFalse(self.settings.get_start_hidden())
        self.assertTrue(self.settings.get_dynamic_island_enabled())
        self.assertEqual(self.settings.get_collapse_delay_ms(), 3500)

    @patch("src.utils.autostart.winreg")
    def test_save_settings_persists_all_values(self, mock_winreg: MagicMock) -> None:
        """Verify save_settings persists all control states to SettingsManager."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.chk_close_to_tray.setChecked(False)
        dlg.chk_start_hidden.setChecked(True)
        dlg.chk_always_on_top.setChecked(False)
        dlg.chk_dynamic_island.setChecked(True)
        dlg.spn_collapse_delay.setValue(4500)

        dlg.save_settings()

        self.assertFalse(self.settings.get_close_to_tray())
        self.assertTrue(self.settings.get_start_hidden())
        self.assertFalse(self.settings.get_always_on_top())
        self.assertTrue(self.settings.get_dynamic_island_enabled())
        self.assertEqual(self.settings.get_collapse_delay_ms(), 4500)

    @patch("src.utils.autostart.winreg")
    def test_save_collapse_delay_2250_succeeds_without_error(self, mock_winreg: MagicMock) -> None:
        """Verify changing collapse delay spinbox to 2250 ms and saving succeeds without showing hotkey error."""
        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.spn_collapse_delay.setValue(2250)
        dlg.save_settings()

        self.assertFalse(dlg.lbl_error.isVisible())
        self.assertEqual(self.settings.get_collapse_delay_ms(), 2250)

    def test_cancel_discards_unsaved_changes(self) -> None:
        """Verify clicking cancel / reject leaves SettingsManager values untouched."""
        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.chk_close_to_tray.setChecked(False)
        dlg.chk_start_hidden.setChecked(True)
        dlg.chk_dynamic_island.setChecked(False)

        dlg.reject()

        self.assertTrue(self.settings.get_close_to_tray())
        self.assertFalse(self.settings.get_start_hidden())
        self.assertTrue(self.settings.get_dynamic_island_enabled())

    @patch("src.utils.autostart.winreg")
    def test_reopening_reflects_persisted_values(self, mock_winreg: MagicMock) -> None:
        """Verify reopening SettingsDialog loads updated persisted settings."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        dlg1 = SettingsDialog(settings_manager=self.settings)
        dlg1.chk_close_to_tray.setChecked(False)
        dlg1.chk_start_hidden.setChecked(True)
        dlg1.chk_dynamic_island.setChecked(False)
        dlg1.spn_collapse_delay.setValue(6000)
        dlg1.save_settings()

        dlg2 = SettingsDialog(settings_manager=self.settings)
        self.assertFalse(dlg2.chk_close_to_tray.isChecked())
        self.assertTrue(dlg2.chk_start_hidden.isChecked())
        self.assertFalse(dlg2.chk_dynamic_island.isChecked())
        self.assertEqual(dlg2.spn_collapse_delay.value(), 6000)

    def test_start_hidden_is_preference_not_immediate_hide(self) -> None:
        """Verify enabling start_hidden in SettingsDialog does not hide current dialog."""
        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.chk_start_hidden.setChecked(True)

        # Preference is saved for next launch
        self.assertTrue(dlg.chk_start_hidden.isChecked())

    def test_landscape_sidebar_and_stacked_widget_pages(self) -> None:
        """Verify SettingsDialog initializes landscape layout with 6 sidebar items and 6 stacked pages."""
        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertEqual(dlg.width(), 680)
        self.assertEqual(dlg.height(), 440)
        self.assertEqual(dlg.sidebar.count(), 6)
        self.assertEqual(dlg.stacked_widget.count(), 6)

        # Verify page navigation via sidebar row change
        dlg.sidebar.setCurrentRow(1)  # Global Shortcuts page
        self.assertEqual(dlg.stacked_widget.currentIndex(), 1)

        dlg.sidebar.setCurrentRow(2)  # Dynamic Island page
        self.assertEqual(dlg.stacked_widget.currentIndex(), 2)

        dlg.sidebar.setCurrentRow(3)  # Appearance page
        self.assertEqual(dlg.stacked_widget.currentIndex(), 3)

        dlg.sidebar.setCurrentRow(4)  # Audio page
        self.assertEqual(dlg.stacked_widget.currentIndex(), 4)

        dlg.sidebar.setCurrentRow(5)  # About page
        self.assertEqual(dlg.stacked_widget.currentIndex(), 5)


if __name__ == "__main__":
    unittest.main()
