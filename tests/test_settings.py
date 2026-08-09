"""Unit tests for src/core/settings.py SettingsManager and QSettings persistence."""

import sys
import unittest
from unittest.mock import MagicMock
from PySide6.QtCore import QObject, QSettings
from PySide6.QtWidgets import QApplication

from src.core.settings import SettingsManager


class TestSettingsManager(unittest.TestCase):
    """Test suite for SettingsManager defaults, persistence, signal emissions, and typing."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a QApplication instance exists for Qt settings signals."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self) -> None:
        """Create an isolated QSettings store for each test and clear stored keys."""
        self.test_qs = QSettings("KrishnaOSTest", "MediaDockTest")
        self.test_qs.clear()
        self.settings = SettingsManager(qsettings=self.test_qs)

    def tearDown(self) -> None:
        """Clean up isolated QSettings store after each test."""
        self.test_qs.clear()

    def test_default_values_and_types(self) -> None:
        """Verify default values and strict type casting for un-set keys."""
        self.assertIsInstance(self.settings.get_close_to_tray(), bool)
        self.assertTrue(self.settings.get_close_to_tray())

        self.assertIsInstance(self.settings.get_start_hidden(), bool)
        self.assertFalse(self.settings.get_start_hidden())

        self.assertIsInstance(self.settings.get_always_on_top(), bool)
        self.assertTrue(self.settings.get_always_on_top())

        self.assertIsInstance(self.settings.get_remember_position(), bool)
        self.assertTrue(self.settings.get_remember_position())

        pos_x, pos_y = self.settings.get_window_position()
        self.assertIsInstance(pos_x, int)
        self.assertIsInstance(pos_y, int)
        self.assertEqual((pos_x, pos_y), (-1, -1))

    def test_getters_and_setters(self) -> None:
        """Verify typed setters update values cleanly."""
        self.settings.set_close_to_tray(False)
        self.assertFalse(self.settings.get_close_to_tray())

        self.settings.set_start_hidden(True)
        self.assertTrue(self.settings.get_start_hidden())

        self.settings.set_always_on_top(False)
        self.assertFalse(self.settings.get_always_on_top())

        self.settings.set_remember_position(False)
        self.assertFalse(self.settings.get_remember_position())

        self.settings.set_window_position(300, 450)
        self.assertEqual(self.settings.get_window_position(), (300, 450))

    def test_persistence_across_instances(self) -> None:
        """Verify settings written by one SettingsManager instance persist for another instance."""
        self.settings.set_close_to_tray(False)
        self.settings.set_start_hidden(True)
        self.settings.set_window_position(120, 240)

        # Create second manager with same QSettings store
        second_qs = QSettings("KrishnaOSTest", "MediaDockTest")
        second_mgr = SettingsManager(qsettings=second_qs)

        self.assertFalse(second_mgr.get_close_to_tray())
        self.assertTrue(second_mgr.get_start_hidden())
        self.assertEqual(second_mgr.get_window_position(), (120, 240))

    def test_settings_changed_signal_emission(self) -> None:
        """Verify settings_changed signal is emitted with (key, value) when a setting changes."""
        mock_slot = MagicMock()
        self.settings.settings_changed.connect(mock_slot)

        self.settings.set_close_to_tray(False)
        mock_slot.assert_called_once_with("general/close_to_tray", False)

        mock_slot.reset_mock()
        self.settings.set_window_position(100, 200)
        self.assertEqual(mock_slot.call_count, 2)
        mock_slot.assert_any_call("window/pos_x", 100)
        mock_slot.assert_any_call("window/pos_y", 200)

    def test_setting_same_value_does_not_emit_signal(self) -> None:
        """Verify setting an existing unchanged value does not emit settings_changed unnecessarily."""
        mock_slot = MagicMock()
        self.settings.settings_changed.connect(mock_slot)

        # Value is already True by default
        self.settings.set_close_to_tray(True)
        mock_slot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
