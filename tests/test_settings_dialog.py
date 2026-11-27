"""Unit tests for src/ui/settings_dialog.py SettingsDialog UI component."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QLabel

from src.core.settings import SettingsManager
from src.ui.main_window import MainWindow
from src.ui.settings_dialog import SettingsDialog, GITHUB_REPO_URL


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
        """Verify SettingsDialog initializes spacious landscape layout with 6 sidebar items and 6 stacked pages."""
        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertGreaterEqual(dlg.width(), 780)
        self.assertGreaterEqual(dlg.height(), 560)
        self.assertEqual(dlg.minimumWidth(), 780)
        self.assertEqual(dlg.minimumHeight(), 560)
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

    def test_audio_equalizer_ui_controls_initialization(self) -> None:
        """Verify audio boost, tone sliders, and 5-band EQ controls exist and initialize with defaults."""
        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertIsNotNone(dlg.chk_eq_enabled)
        self.assertIsNotNone(dlg.sld_preamp)
        self.assertIsNotNone(dlg.sld_bass)
        self.assertIsNotNone(dlg.sld_clarity)
        self.assertIsNotNone(dlg.sld_treble)
        self.assertIsNotNone(dlg.sld_noise_gate)
        self.assertIsNotNone(dlg.cmb_preset)
        self.assertEqual(len(dlg.eq_band_sliders), 5)
        self.assertIsNotNone(dlg.btn_reset_eq)

        # Initial default values
        self.assertTrue(dlg.chk_eq_enabled.isChecked())
        self.assertEqual(dlg.sld_preamp.value(), 0)
        self.assertEqual(dlg.sld_bass.value(), 0)
        self.assertEqual(dlg.sld_clarity.value(), 0)
        self.assertEqual(dlg.sld_treble.value(), 0)
        self.assertEqual(dlg.sld_noise_gate.value(), 5)
        self.assertEqual(dlg.cmb_preset.currentText(), "Flat")

    @patch("src.utils.autostart.winreg")
    def test_audio_equalizer_ui_save_and_reload(self, mock_winreg: MagicMock) -> None:
        """Verify modifying audio boost and tone sliders saves and persists into SettingsManager."""
        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.sld_preamp.setValue(50)  # +5.0 dB
        dlg.sld_bass.setValue(40)    # +4.0 dB
        dlg.sld_clarity.setValue(30) # +3.0 dB
        dlg.sld_treble.setValue(-20) # -2.0 dB
        dlg.sld_noise_gate.setValue(12)
        dlg.sld_band_60.setValue(35)
        dlg.save_settings()

        self.assertAlmostEqual(self.settings.get_preamp_boost_db(), 5.0, places=1)
        self.assertAlmostEqual(self.settings.get_bass_db(), 4.0, places=1)
        self.assertAlmostEqual(self.settings.get_clarity_db(), 3.0, places=1)
        self.assertAlmostEqual(self.settings.get_treble_db(), -2.0, places=1)
        self.assertEqual(self.settings.get_noise_gate_percent(), 12)
        self.assertAlmostEqual(self.settings.get_eq_bands()[0], 3.5, places=1)

    def test_audio_preset_selection_and_reset(self) -> None:
        """Verify selecting a preset updates sliders and clicking reset restores Flat."""
        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.cmb_preset.setCurrentText("Bass Boost")

        # 60Hz band should have updated
        self.assertGreater(dlg.sld_band_60.value(), 0)

        # Reset Flat button
        dlg.btn_reset_eq.click()
        self.assertEqual(dlg.sld_preamp.value(), 0)
        self.assertEqual(dlg.sld_bass.value(), 0)
        self.assertEqual(dlg.sld_band_60.value(), 0)
        self.assertEqual(dlg.cmb_preset.currentText(), "Flat")

    def test_appearance_hex_controls_and_no_status_colors(self) -> None:
        """Verify Appearance page uses hex code inputs for Background/Border only and omits status colors."""
        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertEqual(dlg.txt_bg_color_hex.text(), "#000000")
        self.assertEqual(dlg.txt_border_color_hex.text(), "#000000")
        self.assertIsNotNone(dlg.btn_reset_appearance)

        appearance_page = dlg.stacked_widget.widget(3)
        all_texts = " ".join(lbl.text() for lbl in appearance_page.findChildren(QLabel))
        self.assertNotIn("Active Status", all_texts)
        self.assertNotIn("Inactive Status", all_texts)
        self.assertNotIn("non-customizable", all_texts.lower())

    @patch("src.utils.autostart.winreg")
    def test_appearance_hex_save_and_live_window_update(self, mock_winreg: MagicMock) -> None:
        """Verify saving custom hex colors persists to SettingsManager and updates MainWindow live."""
        win = MainWindow(settings_manager=self.settings)
        dlg = SettingsDialog(settings_manager=self.settings, parent=win)

        dlg.txt_bg_color_hex.setText("121820")
        dlg.txt_border_color_hex.setText("#00ff7f")
        dlg.save_settings()

        self.assertEqual(self.settings.get_notch_bg_color(), "#121820")
        self.assertEqual(self.settings.get_notch_border_color(), "#00FF7F")
        self.assertEqual(win._bg_color, QColor("#121820"))
        self.assertEqual(win._border_color, QColor("#00FF7F"))
        self.assertEqual(win.notch_widget._bg_color, QColor("#121820"))
        self.assertEqual(win.notch_widget._border_color, QColor("#00FF7F"))

    @patch("src.utils.autostart.winreg")
    def test_appearance_invalid_hex_blocks_save_and_focuses_page(self, mock_winreg: MagicMock) -> None:
        """Verify malformed hex input prevents persistence and highlights the Appearance page error."""
        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.txt_bg_color_hex.setText("#ZZZZZZ")
        dlg.save_settings()

        self.assertEqual(dlg.sidebar.currentRow(), 3)
        self.assertFalse(dlg.lbl_appearance_error.isHidden())
        self.assertEqual(self.settings.get_notch_bg_color(), "#000000")

    def test_appearance_reset_defaults_restores_black(self) -> None:
        """Verify Reset to Default restores #000000 in both hex inputs."""
        dlg = SettingsDialog(settings_manager=self.settings)
        dlg.txt_bg_color_hex.setText("#1A1A20")
        dlg.txt_border_color_hex.setText("#00FF7F")
        dlg.btn_reset_appearance.click()

        self.assertEqual(dlg.txt_bg_color_hex.text(), "#000000")
        self.assertEqual(dlg.txt_border_color_hex.text(), "#000000")

    def test_about_page_includes_github_link_and_actions(self) -> None:
        """Verify About page displays clickable project GitHub repository link and action buttons."""
        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertIn(GITHUB_REPO_URL, dlg.lbl_github_link.text())
        self.assertTrue(dlg.lbl_github_link.openExternalLinks())
        self.assertIsNotNone(dlg.btn_open_github)
        self.assertIsNotNone(dlg.btn_report_issue)

    def test_settings_dialog_gaussian_blur_backdrop_enabled(self) -> None:
        """Verify SettingsDialog enables translucent glass background and Windows Gaussian blur mode."""
        from PySide6.QtCore import Qt
        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertTrue(dlg.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertIn(dlg._blur_backdrop_mode, ("dwm_acrylic", "composition_acrylic", "translucent"))
        self.assertIn("transparent", dlg.styleSheet())

    @patch("src.utils.autostart.winreg")
    def test_appearance_gradient_presets_styles_and_save(self, mock_winreg: MagicMock) -> None:
        """Verify selecting gradient presets/styles updates previews and persists cleanly to MainWindow."""
        from src.ui.main_window import DynamicIslandState
        win = MainWindow(settings_manager=self.settings)
        dlg = SettingsDialog(settings_manager=self.settings, parent=win)

        preset_idx = dlg.combo_gradient_preset.findData("Sunset Ember")
        self.assertGreaterEqual(preset_idx, 0)
        dlg.combo_gradient_preset.setCurrentIndex(preset_idx)
        self.assertEqual(dlg.combo_bg_mode.currentData(), "gradient")
        self.assertEqual(dlg.txt_grad_color_1.text(), "#230812")
        self.assertEqual(dlg.txt_grad_color_3.text(), "#D96B27")

        # Editing stop hex switches preset to Custom & supports optional empty mid stop
        dlg.txt_grad_color_2.setText("")
        dlg.txt_grad_color_3.setText("#00ff7f")
        self.assertEqual(dlg.combo_gradient_preset.currentData(), "Custom")

        # Select radial/conic/mesh styles and save
        for style_key in ("radial", "conic", "mesh"):
            idx = dlg.combo_gradient_style.findData(style_key)
            self.assertGreaterEqual(idx, 0)
            dlg.combo_gradient_style.setCurrentIndex(idx)
            dlg.save_settings()
            self.assertEqual(self.settings.get_gradient_style(), style_key)
            self.assertEqual(win._appearance.bg_mode, "gradient")
            self.assertEqual(win._appearance.gradient_style, style_key)
            self.assertEqual(win.notch_widget._appearance.gradient_style, style_key)

        win.set_state(DynamicIslandState.EXPANDED, animate=False)
        win.repaint()
        win.notch_widget.repaint()
        dlg.preview_collapsed_notch.repaint()
        dlg.preview_expanded_card.repaint()

    @patch("src.utils.autostart.winreg")
    def test_appearance_custom_banner_images_expanded_and_collapsed(self, mock_winreg: MagicMock) -> None:
        """Verify separate expanded/collapsed banner images persist, copy, crop, and paint safely."""
        import tempfile
        from PySide6.QtGui import QImage
        from src.ui.main_window import DynamicIslandState

        exp_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        col_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        exp_tmp.close()
        col_tmp.close()
        try:
            img_exp = QImage(160, 80, QImage.Format.Format_ARGB32)
            img_exp.fill(QColor("#2A4D8F"))
            self.assertTrue(img_exp.save(exp_tmp.name, "PNG"))

            img_col = QImage(120, 40, QImage.Format.Format_ARGB32)
            img_col.fill(QColor("#8E1D41"))
            self.assertTrue(img_col.save(col_tmp.name, "PNG"))

            win = MainWindow(settings_manager=self.settings)
            dlg = SettingsDialog(settings_manager=self.settings, parent=win)

            img_mode_idx = dlg.combo_bg_mode.findData("image")
            dlg.combo_bg_mode.setCurrentIndex(img_mode_idx)
            dlg.txt_expanded_image_path.setText(exp_tmp.name)

            # Copy Expanded to Collapsed button works
            dlg.btn_copy_expanded_to_collapsed.click()
            self.assertEqual(dlg.txt_collapsed_image_path.text(), exp_tmp.name)

            # Now set distinct collapsed image, top alignment, and 45% dim
            dlg.txt_collapsed_image_path.setText(col_tmp.name)
            align_idx = dlg.combo_image_alignment.findData("top")
            dlg.combo_image_alignment.setCurrentIndex(align_idx)
            dlg.sld_image_dim.setValue(45)
            dlg.save_settings()

            self.assertEqual(self.settings.get_appearance_bg_mode(), "image")
            self.assertEqual(self.settings.get_expanded_image_path(), exp_tmp.name)
            self.assertEqual(self.settings.get_collapsed_image_path(), col_tmp.name)
            self.assertEqual(self.settings.get_image_alignment(), "top")
            self.assertEqual(self.settings.get_image_dim_percent(), 45)
            self.assertEqual(win._appearance.expanded_image_path, exp_tmp.name)
            self.assertEqual(win.notch_widget._appearance.collapsed_image_path, col_tmp.name)

            win.set_state(DynamicIslandState.EXPANDED, animate=False)
            win.repaint()
            win.notch_widget.repaint()
            dlg.preview_collapsed_notch.repaint()
            dlg.preview_expanded_card.repaint()
        finally:
            for p in (exp_tmp.name, col_tmp.name):
                if os.path.exists(p):
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

    @patch("src.utils.autostart.winreg")
    def test_appearance_missing_banner_image_blocks_save(self, mock_winreg: MagicMock) -> None:
        """Verify choosing Image mode without a valid banner image blocks save and warns on Appearance page."""
        dlg = SettingsDialog(settings_manager=self.settings)
        img_mode_idx = dlg.combo_bg_mode.findData("image")
        dlg.combo_bg_mode.setCurrentIndex(img_mode_idx)
        dlg.save_settings()

        self.assertEqual(dlg.sidebar.currentRow(), 3)
        self.assertFalse(dlg.lbl_appearance_error.isHidden())
        self.assertEqual(self.settings.get_appearance_bg_mode(), "solid")

    def test_audio_connection_controls_and_reject_restore(self) -> None:
        """Verify Audio page exposes computer connection controls and Cancel restores saved audio profile."""
        from src.core.models import VolumeState

        mock_core = MagicMock()
        mock_core.get_volume_state.return_value = VolumeState(volume_percent=52, is_muted=False, is_supported=True)
        mock_core._analyzer = MagicMock()

        dlg = SettingsDialog(settings_manager=self.settings, media_core=mock_core)
        self.assertIn("52%", dlg.lbl_volume_status.text())
        self.assertIsNotNone(dlg.btn_connect_audio)
        self.assertIsNotNone(dlg.btn_audio_devices)
        self.assertIsNotNone(dlg.btn_apply_audio_now)

        dlg.sld_bass.setValue(60)
        dlg.btn_apply_audio_now.click()
        mock_core._analyzer.set_eq_profile.assert_called()

        dlg.reject()
        mock_core.sync_audio_settings.assert_called_with(self.settings)


if __name__ == "__main__":
    unittest.main()
