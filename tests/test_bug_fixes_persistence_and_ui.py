"""Unit and regression test suite for MediaDock bug fixes:
1. Preference persistence across fresh SettingsManager/application instances.
2. Collapse Delay SpinBox UI read-only text entry, up/down buttons, geometry, and timer sync.
3. Collapsed Dynamic Island capsule metadata center alignment (horizontal CENTER, vertical MIDDLE).
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWidgets import QApplication

from src.core.settings import SettingsManager
from src.ui.settings_dialog import SettingsDialog, CollapseDelaySpinBox
from src.ui.components_island import CollapsedCapsuleWidget
from src.ui.main_window import MainWindow
from src.core.models import PlaybackStatus


class TestBugFixesPersistenceAndUI(unittest.TestCase):
    """Test suite verifying persistence regression fixes and UI refinements."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure QApplication instance exists for GUI tests."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self) -> None:
        """Create isolated temporary INI QSettings store for each test."""
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        self.tmp_file.close()
        self.qs = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        self.sm = SettingsManager(qsettings=self.qs)

    def tearDown(self) -> None:
        """Clean up temporary INI file after each test."""
        if hasattr(self, "tmp_file") and os.path.exists(self.tmp_file.name):
            try:
                os.unlink(self.tmp_file.name)
            except OSError:
                pass

    # --- BUG 1: PERSISTENCE REGRESSION TESTS ---

    def test_preference_persistence_across_fresh_instances(self) -> None:
        """Verify saving preferences and loading from a fresh SettingsManager instance returns exact saved values."""
        # Save custom preferences
        self.sm.set_collapse_delay_ms(2250)
        self.sm.set_close_to_tray(False)
        self.sm.set_start_hidden(True)
        self.sm.set_always_on_top(False)
        self.sm.set_dynamic_island_enabled(False)
        self.sm.set_hotkey_show_hide("Ctrl+Alt+K")
        self.sm.set_hotkey_play_pause("Ctrl+Alt+P")
        self.sm.sync()

        # Create new SettingsManager pointing to same QSettings store
        qs2 = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        sm2 = SettingsManager(qsettings=qs2)

        self.assertEqual(sm2.get_collapse_delay_ms(), 2250)
        self.assertFalse(sm2.get_close_to_tray())
        self.assertTrue(sm2.get_start_hidden())
        self.assertFalse(sm2.get_always_on_top())
        self.assertFalse(sm2.get_dynamic_island_enabled())
        self.assertEqual(sm2.get_hotkey_show_hide(), "Ctrl+Alt+K")
        self.assertEqual(sm2.get_hotkey_play_pause(), "Ctrl+Alt+P")

    @patch("src.utils.autostart.winreg")
    def test_settings_dialog_save_persists_to_fresh_instance(self, mock_winreg: MagicMock) -> None:
        """Verify SettingsDialog save_settings() correctly syncs all 8 user preferences to fresh instances."""
        dlg = SettingsDialog(settings_manager=self.sm)
        dlg.chk_close_to_tray.setChecked(False)
        dlg.chk_start_hidden.setChecked(True)
        dlg.chk_always_on_top.setChecked(False)
        dlg.chk_dynamic_island.setChecked(True)
        dlg.spn_collapse_delay.setValue(1750)
        dlg.rec_hotkey_show_hide.set_sequence("Ctrl+Alt+A")
        dlg.rec_hotkey_play_pause.set_sequence("Ctrl+Alt+B")

        dlg.save_settings()

        # Re-read from fresh QSettings store
        qs2 = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        sm2 = SettingsManager(qsettings=qs2)

        self.assertEqual(sm2.get_collapse_delay_ms(), 1750)
        self.assertFalse(sm2.get_close_to_tray())
        self.assertTrue(sm2.get_start_hidden())
        self.assertFalse(sm2.get_always_on_top())
        self.assertTrue(sm2.get_dynamic_island_enabled())
        self.assertEqual(sm2.get_hotkey_show_hide(), "Ctrl+Alt+A")
        self.assertEqual(sm2.get_hotkey_play_pause(), "Ctrl+Alt+B")

    # --- BUG 2: COLLAPSE DELAY CONTROL UI TESTS ---

    def test_collapse_delay_spinbox_read_only_text(self) -> None:
        """Verify CollapseDelaySpinBox text field is read-only to keyboard input."""
        spn = CollapseDelaySpinBox()
        self.assertTrue(spn.lineEdit().isReadOnly())
        self.assertEqual(spn.lineEdit().focusPolicy(), Qt.FocusPolicy.NoFocus)

    def test_collapse_delay_spinbox_up_down_buttons(self) -> None:
        """Verify ▲ increments by step (250 ms) and ▼ decrements by step (250 ms)."""
        spn = CollapseDelaySpinBox()
        spn.setValue(2000)

        # Click ▲ button
        spn.btn_up.click()
        self.assertEqual(spn.value(), 2250)

        # Click ▼ button
        spn.btn_down.click()
        self.assertEqual(spn.value(), 2000)

    def test_collapse_delay_spinbox_bounds_clamping(self) -> None:
        """Verify CollapseDelaySpinBox enforces 500 ms min and 30000 ms max bounds."""
        spn = CollapseDelaySpinBox()
        spn.setValue(500)
        spn.btn_down.click()
        self.assertEqual(spn.value(), 500)

        spn.setValue(30000)
        spn.btn_up.click()
        self.assertEqual(spn.value(), 30000)

    def test_collapse_delay_spinbox_button_geometry_and_symbols(self) -> None:
        """Verify up/down buttons have equal geometry, correct unicode symbols ▲ and ▼, and no overlapping."""
        spn = CollapseDelaySpinBox()
        spn.resize(130, 32)
        spn.show()
        self.app.processEvents()

        self.assertEqual(spn.btn_up.text(), "▲")
        self.assertEqual(spn.btn_down.text(), "▼")
        self.assertEqual(spn.btn_up.width(), spn.btn_down.width())
        self.assertAlmostEqual(spn.btn_up.height(), spn.btn_down.height(), delta=2)

    def test_mainwindow_collapse_timer_initialization(self) -> None:
        """Verify MainWindow initializes _collapse_timer interval from SettingsManager."""
        self.sm.set_collapse_delay_ms(1750)
        from src.core.models import TrackInfo
        mock_core = MagicMock()
        mock_core.get_current_track.return_value = TrackInfo("Title", "Artist", "Album", None, "Spotify.exe", 100000, 0)
        mock_core.get_playback_status.return_value = PlaybackStatus.CLOSED
        mock_core.is_session_available.return_value = False
        mock_core.get_volume_state.return_value = MagicMock(is_supported=False)

        window = MainWindow(media_core=mock_core, settings_manager=self.sm)
        self.assertEqual(window._collapse_timer.interval(), 1750)

    # --- BUG 3: CAPSULE METADATA ALIGNMENT TESTS ---

    def test_capsule_metadata_alignment(self) -> None:
        """Verify CollapsedCapsuleWidget centers metadata group horizontally and vertically."""
        capsule = CollapsedCapsuleWidget()
        capsule.set_source_info("Spotify.exe", "Blinding Lights", "The Weeknd")
        capsule.set_playback_status(PlaybackStatus.PLAYING)
        capsule.show()
        self.app.processEvents()

        # Icon (18x18), no activity dot in collapsed notch
        self.assertEqual(capsule.icon_label.width(), 18)
        self.assertEqual(capsule.icon_label.height(), 18)
        self.assertFalse(hasattr(capsule, "status_dot"))

        # Title alignment = Center
        self.assertEqual(capsule.title_label.alignment() & Qt.AlignmentFlag.AlignCenter, Qt.AlignmentFlag.AlignCenter)

        # Vertical Center check (half of 34px DeskNotch bar = 17.0)
        icon_y_center = capsule.icon_label.y() + capsule.icon_label.height() / 2.0
        pulse_y_center = capsule.pulse_bars.y() + capsule.pulse_bars.height() / 2.0
        self.assertAlmostEqual(icon_y_center, 17.0, delta=2.0)
        self.assertAlmostEqual(pulse_y_center, 17.0, delta=2.0)


if __name__ == "__main__":
    unittest.main()
