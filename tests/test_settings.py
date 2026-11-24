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
        """Create an isolated temporary INI QSettings store for each test."""
        import tempfile
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        self.tmp_file.close()
        self.test_qs = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        self.settings = SettingsManager(qsettings=self.test_qs)

    def tearDown(self) -> None:
        """Clean up isolated temporary INI file after each test."""
        import os
        if hasattr(self, "tmp_file") and os.path.exists(self.tmp_file.name):
            try:
                os.unlink(self.tmp_file.name)
            except OSError:
                pass



    def test_default_values_and_types(self) -> None:
        """Verify default values and strict type casting for un-set keys."""
        self.assertIsInstance(self.settings.get_close_to_tray(), bool)
        self.assertTrue(self.settings.get_close_to_tray())

        self.assertIsInstance(self.settings.get_start_hidden(), bool)
        self.assertFalse(self.settings.get_start_hidden())

        self.assertIsInstance(self.settings.get_always_on_top(), bool)
        self.assertTrue(self.settings.get_always_on_top())

        self.assertIsInstance(self.settings.get_dynamic_island_enabled(), bool)
        self.assertTrue(self.settings.get_dynamic_island_enabled())

        self.assertIsInstance(self.settings.get_collapse_delay_ms(), int)
        self.assertEqual(self.settings.get_collapse_delay_ms(), 3500)

    def test_getters_and_setters(self) -> None:
        """Verify typed setters update values cleanly."""
        self.settings.set_close_to_tray(False)
        self.assertFalse(self.settings.get_close_to_tray())

        self.settings.set_start_hidden(True)
        self.assertTrue(self.settings.get_start_hidden())

        self.settings.set_always_on_top(False)
        self.assertFalse(self.settings.get_always_on_top())

        self.settings.set_dynamic_island_enabled(False)
        self.assertFalse(self.settings.get_dynamic_island_enabled())

        self.settings.set_collapse_delay_ms(5000)
        self.assertEqual(self.settings.get_collapse_delay_ms(), 5000)

    def test_collapse_delay_bounds_clamping(self) -> None:
        """Verify set_collapse_delay_ms clamps inputs between 500 ms and 30000 ms safely."""
        self.settings.set_collapse_delay_ms(2250)
        self.assertEqual(self.settings.get_collapse_delay_ms(), 2250)

        # Under min threshold (500) -> clamped to 500
        self.settings.set_collapse_delay_ms(100)
        self.assertEqual(self.settings.get_collapse_delay_ms(), 500)

        # Over max threshold (30000) -> clamped to 30000
        self.settings.set_collapse_delay_ms(45000)
        self.assertEqual(self.settings.get_collapse_delay_ms(), 30000)

    def test_persistence_across_instances(self) -> None:
        """Verify settings written by one SettingsManager instance persist for another instance."""
        self.settings.set_close_to_tray(False)
        self.settings.set_start_hidden(True)
        self.settings.set_dynamic_island_enabled(False)
        self.settings.set_collapse_delay_ms(4000)

        # Create second manager with same QSettings store
        second_qs = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        second_mgr = SettingsManager(qsettings=second_qs)

        self.assertFalse(second_mgr.get_close_to_tray())
        self.assertTrue(second_mgr.get_start_hidden())
        self.assertFalse(second_mgr.get_dynamic_island_enabled())
        self.assertEqual(second_mgr.get_collapse_delay_ms(), 4000)


    def test_settings_changed_signal_emission(self) -> None:
        """Verify settings_changed signal is emitted with (key, value) when a setting changes."""
        mock_slot = MagicMock()
        self.settings.settings_changed.connect(mock_slot)

        self.settings.set_close_to_tray(False)
        mock_slot.assert_called_once_with("general/close_to_tray", False)

        mock_slot.reset_mock()
        self.settings.set_collapse_delay_ms(4000)
        mock_slot.assert_called_once_with("dynamic_island/collapse_delay_ms", 4000)

    def test_setting_same_value_does_not_emit_signal(self) -> None:
        """Verify setting an existing unchanged value does not emit settings_changed unnecessarily."""
        mock_slot = MagicMock()
        self.settings.settings_changed.connect(mock_slot)

        # Value is already True by default
        self.settings.set_close_to_tray(True)
        mock_slot.assert_not_called()

    def test_settings_manager_sync(self) -> None:
        """Verify sync() method flushes settings without exception."""
        self.settings.set_collapse_delay_ms(4500)
        self.settings.sync()
        self.assertEqual(self.settings.get_collapse_delay_ms(), 4500)

    def test_default_qsettings_store_organization(self) -> None:
        """Verify SettingsManager default store targets KrishnaOS/MediaDock organization."""
        default_mgr = SettingsManager()
        self.assertEqual(default_mgr._settings.organizationName(), "KrishnaOS")
        self.assertEqual(default_mgr._settings.applicationName(), "MediaDock")

    def test_main_window_force_close_and_close_event(self) -> None:
        """Verify MainWindow force_close sets _is_quitting and closeEvent accepts closing."""
        from PySide6.QtGui import QCloseEvent
        from src.ui.main_window import MainWindow

        win = MainWindow(settings_manager=self.settings)
        self.settings.set_close_to_tray(True)

        # Spontaneous user close event while running -> ignored to hide to tray
        evt1 = QCloseEvent()
        win.closeEvent(evt1)
        self.assertFalse(evt1.isAccepted())

        # Programmatic force_close (e.g. exit menu / OS shutdown) -> accepted
        win.force_close()
        evt2 = QCloseEvent()
        win.closeEvent(evt2)
        self.assertTrue(evt2.isAccepted())

    def test_preferences_persist_across_tray_exit_and_relaunch(self) -> None:
        """Verify non-default preferences persist cleanly across application tray exit simulation and fresh launch."""
        from src.ui.settings_dialog import SettingsDialog
        from src.ui.main_window import MainWindow

        win = MainWindow(settings_manager=self.settings)

        # 1. Modify preferences via SettingsDialog save_settings
        dialog = SettingsDialog(settings_manager=self.settings, parent=win)
        dialog.chk_close_to_tray.setChecked(False)
        dialog.chk_start_hidden.setChecked(True)
        dialog.chk_always_on_top.setChecked(False)
        dialog.spn_collapse_delay.setValue(6500)
        dialog.save_settings()

        # 2. Simulate System Tray exit sync
        self.settings.sync()

        # 3. Instantiate fresh QSettings and SettingsManager instance
        fresh_qs = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        fresh_mgr = SettingsManager(qsettings=fresh_qs)

        # 4. Assert all saved values persist cleanly
        self.assertFalse(fresh_mgr.get_close_to_tray())
        self.assertTrue(fresh_mgr.get_start_hidden())
        self.assertFalse(fresh_mgr.get_always_on_top())
        self.assertEqual(fresh_mgr.get_collapse_delay_ms(), 6500)

    def test_audio_equalizer_settings_persistence(self) -> None:
        """Verify audio boost, tone controls, noise gate, and 5-band EQ persist cleanly."""
        self.settings.set_preamp_boost_db(4.5)
        self.settings.set_bass_db(6.0)
        self.settings.set_clarity_db(3.5)
        self.settings.set_treble_db(-1.5)
        self.settings.set_noise_gate_percent(15)
        self.settings.set_eq_preset("Electronic")
        self.settings.set_eq_bands([4.0, 2.0, -1.0, 2.5, 4.0])
        self.settings.set_eq_enabled(True)

        fresh_qs = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        fresh_mgr = SettingsManager(qsettings=fresh_qs)

        self.assertAlmostEqual(fresh_mgr.get_preamp_boost_db(), 4.5, places=1)
        self.assertAlmostEqual(fresh_mgr.get_bass_db(), 6.0, places=1)
        self.assertAlmostEqual(fresh_mgr.get_clarity_db(), 3.5, places=1)
        self.assertAlmostEqual(fresh_mgr.get_treble_db(), -1.5, places=1)
        self.assertEqual(fresh_mgr.get_noise_gate_percent(), 15)
        self.assertEqual(fresh_mgr.get_eq_preset(), "Electronic")
        self.assertEqual(fresh_mgr.get_eq_bands(), [4.0, 2.0, -1.0, 2.5, 4.0])
        self.assertTrue(fresh_mgr.get_eq_enabled())

    def test_audio_settings_clamping(self) -> None:
        """Verify bounds clamping on audio boost, tone controls, and noise gate."""
        self.settings.set_preamp_boost_db(25.0)  # max 12.0
        self.assertEqual(self.settings.get_preamp_boost_db(), 12.0)

        self.settings.set_preamp_boost_db(-5.0)  # min 0.0
        self.assertEqual(self.settings.get_preamp_boost_db(), 0.0)

        self.settings.set_bass_db(20.0)  # max 12.0
        self.assertEqual(self.settings.get_bass_db(), 12.0)

        self.settings.set_noise_gate_percent(100)  # max 50%
        self.assertEqual(self.settings.get_noise_gate_percent(), 50)

    def test_advanced_feature_settings(self) -> None:
        """Verify advanced features settings getters, setters, and defaults."""
        self.assertEqual(self.settings.get_expand_trigger(), "hover")
        self.settings.set_expand_trigger("click")
        self.assertEqual(self.settings.get_expand_trigger(), "click")

        self.assertEqual(self.settings.get_hover_intent_delay_ms(), 0)
        self.settings.set_hover_intent_delay_ms(250)
        self.assertEqual(self.settings.get_hover_intent_delay_ms(), 250)

        self.assertTrue(self.settings.get_fullscreen_auto_hide())
        self.settings.set_fullscreen_auto_hide(False)
        self.assertFalse(self.settings.get_fullscreen_auto_hide())

        self.assertEqual(self.settings.get_display_monitor(), "primary")
        self.settings.set_display_monitor("monitor_2")
        self.assertEqual(self.settings.get_display_monitor(), "monitor_2")

        self.assertEqual(self.settings.get_spectrum_mode(), "rms")
        self.settings.set_spectrum_mode("rms")
        self.assertEqual(self.settings.get_spectrum_mode(), "rms")

        self.assertTrue(self.settings.get_lyrics_enabled())
        self.settings.set_lyrics_enabled(False)
        self.assertFalse(self.settings.get_lyrics_enabled())


if __name__ == "__main__":
    unittest.main()
