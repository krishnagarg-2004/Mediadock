"""Unit tests for capsule source icons, spinbox hitbox, pure black border, and interactive shortcut recorder widget."""

import sys
import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor, QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication

from src.core.settings import SettingsManager
from src.ui.theme import COLOR_BG_ISLAND, COLOR_BORDER_ISLAND
from src.ui.components_island import CollapsedCapsuleWidget
from src.ui.frameless_window import FramelessWindow
from src.ui.settings_dialog import SettingsDialog, ShortcutRecorderWidget


class TestShortcutRecorderAndRefinements(unittest.TestCase):
    """Test suite for Phase 9.2 V1 refinements."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure QApplication instance exists for GUI testing."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self) -> None:
        import tempfile
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        self.tmp_file.close()
        self.qs = QSettings(self.tmp_file.name, QSettings.Format.IniFormat)
        self.settings = SettingsManager(qsettings=self.qs)

    def tearDown(self) -> None:
        import os
        if hasattr(self, "tmp_file") and os.path.exists(self.tmp_file.name):
            try:
                os.unlink(self.tmp_file.name)
            except OSError:
                pass

    # 1. Capsule Source Icon Fix Tests
    def test_capsule_source_icon_mapping(self) -> None:
        """Verify capsule sets correct SVG icon pixmap for Spotify, YouTube, VLC, and unknown sources without text glyph fallback."""
        capsule = CollapsedCapsuleWidget()

        capsule.set_source_info("Spotify.exe", "Starboy", "The Weeknd")
        self.assertFalse(capsule.icon_label.pixmap().isNull())

        capsule.set_source_info("chrome.exe", "YouTube Video", "")
        self.assertFalse(capsule.icon_label.pixmap().isNull())

        capsule.set_source_info("vlc.exe", "Sample.mp4", "")
        self.assertFalse(capsule.icon_label.pixmap().isNull())

        capsule.set_source_info("unknown_player.exe", "Track Title", "Artist")
        self.assertFalse(capsule.icon_label.pixmap().isNull())

    # 2. Black Island Border Tests
    def test_black_island_border(self) -> None:
        """Verify capsule and frameless window use pure black #000000 for border token."""
        self.assertEqual(COLOR_BORDER_ISLAND, QColor("#000000"))
        capsule = CollapsedCapsuleWidget()
        self.assertEqual(capsule._border_color, QColor("#000000"))

    # 3. Spinbox Hitbox Configuration
    def test_spinbox_hitbox_styling(self) -> None:
        """Verify QSpinBox style sheet includes subcontrol styling and right padding for clickable button hitboxes."""
        dlg = SettingsDialog(settings_manager=self.settings)
        style = dlg.spn_collapse_delay.styleSheet()
        self.assertIn("padding-right: 34px;", style)
        self.assertIn("QSpinBox::up-button", style)
        self.assertIn("QSpinBox::down-button", style)

    # 4. Shortcut Recorder Widget Tests
    def test_shortcut_recorder_initial_state(self) -> None:
        """Verify ShortcutRecorderWidget initializes with sequence string and pill badges."""
        rec = ShortcutRecorderWidget("Ctrl+Alt+M")
        self.assertEqual(rec.sequence(), "Ctrl+Alt+M")
        self.assertEqual(rec.text(), "Ctrl+Alt+M")
        self.assertFalse(rec.is_recording())
        self.assertEqual(rec.validation_error(), "")

    def test_shortcut_recorder_accepts_valid_2_key_combination(self) -> None:
        """Verify recorder accepts 2-key combination (Ctrl+M)."""
        rec = ShortcutRecorderWidget()
        rec.start_recording()
        self.assertTrue(rec.is_recording())

        # Press Ctrl + M
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_M, Qt.KeyboardModifier.ControlModifier, "M")
        rec.keyPressEvent(event)

        self.assertFalse(rec.is_recording())
        self.assertEqual(rec.sequence(), "Ctrl+M")
        self.assertEqual(rec.validation_error(), "")

    def test_shortcut_recorder_accepts_valid_3_key_combination(self) -> None:
        """Verify recorder accepts 3-key combination (Ctrl+Alt+Space)."""
        rec = ShortcutRecorderWidget()
        rec.start_recording()

        # Press Ctrl + Alt + Space
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier, " ")
        rec.keyPressEvent(event)

        self.assertFalse(rec.is_recording())
        self.assertEqual(rec.sequence(), "Ctrl+Alt+Space")
        self.assertEqual(rec.validation_error(), "")

    def test_shortcut_recorder_rejects_1_key_combination(self) -> None:
        """Verify recorder rejects 1-key combination (isolated key with no modifier)."""
        rec = ShortcutRecorderWidget("Ctrl+Alt+M")
        rec.start_recording()

        # Press M alone with no modifiers
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_M, Qt.KeyboardModifier.NoModifier, "M")
        rec.keyPressEvent(event)

        self.assertFalse(rec.is_recording())
        self.assertIn("at least 2 keys", rec.validation_error())

    def test_shortcut_recorder_rejects_4_key_combination(self) -> None:
        """Verify recorder rejects 4-key combination (Ctrl+Alt+Shift+Win+M)."""
        rec = ShortcutRecorderWidget("Ctrl+Alt+M")
        rec.start_recording()

        # Press Ctrl + Alt + Shift + Win + M (4 modifiers + 1 key = 5 keys > 3)
        mods = (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
            | Qt.KeyboardModifier.ShiftModifier
            | Qt.KeyboardModifier.MetaModifier
        )
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_M, mods, "M")
        rec.keyPressEvent(event)

        self.assertFalse(rec.is_recording())
        self.assertIn("cannot exceed 3 keys", rec.validation_error())

    def test_settings_dialog_uses_shortcut_recorder_widget_not_qlineedit(self) -> None:
        """Verify SettingsDialog actually constructs ShortcutRecorderWidget rather than QLineEdit."""
        from PySide6.QtWidgets import QLineEdit
        dlg = SettingsDialog(settings_manager=self.settings)
        self.assertIsInstance(dlg.rec_hotkey_show_hide, ShortcutRecorderWidget)
        self.assertIsInstance(dlg.rec_hotkey_play_pause, ShortcutRecorderWidget)
        self.assertNotIsInstance(dlg.rec_hotkey_show_hide, QLineEdit)
        self.assertNotIsInstance(dlg.rec_hotkey_play_pause, QLineEdit)

    def test_shortcut_recorder_renders_plus_labels_between_tokens(self) -> None:
        """Verify ShortcutRecorderWidget renders '+' labels between consecutive key pills."""
        from PySide6.QtWidgets import QLabel
        rec = ShortcutRecorderWidget("Ctrl+Shift+M")
        labels = [rec.pills_layout.itemAt(i).widget() for i in range(rec.pills_layout.count()) if rec.pills_layout.itemAt(i).widget()]
        plus_texts = [w.text() for w in labels if isinstance(w, QLabel) and w.text() == "+"]
        self.assertEqual(len(plus_texts), 2)  # Two '+' signs for 3 keys (Ctrl + Shift + M)

    @patch("src.utils.autostart.winreg")
    def test_general_settings_persisted_even_if_hotkey_rebind_fails(self, mock_winreg: MagicMock) -> None:
        """Verify general settings (such as collapse delay) are saved even if hotkey rebind fails."""
        mock_hotkey_mgr = MagicMock()
        mock_hotkey_mgr.rebind_hotkeys.return_value = False  # Simulate registration failure

        dlg = SettingsDialog(settings_manager=self.settings, hotkey_manager=mock_hotkey_mgr)
        dlg.spn_collapse_delay.setValue(2100)
        dlg.rec_hotkey_show_hide.set_sequence("Ctrl+Alt+Z")  # Changed sequence triggers rebind

        dlg.save_settings()

        # General setting should be persisted regardless
        self.assertEqual(self.settings.get_collapse_delay_ms(), 2100)
        self.assertFalse(dlg.lbl_error.isHidden())
        self.assertIn("Failed to register global hotkeys", dlg.lbl_error.text())


if __name__ == "__main__":
    unittest.main()
