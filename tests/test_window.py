"""Unit tests for MediaDock window initialization and configuration."""

import sys
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.frameless_window import FramelessWindow


class TestMediaDockWindow(unittest.TestCase):
    """Test suite verifying window flags, translucent background, and initialization."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a QApplication instance exists for testing GUI components."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_frameless_window_flags(self) -> None:
        """Verify FramelessWindow initializes with correct Qt window flags."""
        window = FramelessWindow()
        flags = window.windowFlags()

        self.assertTrue(flags & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(flags & Qt.WindowType.WindowStaysOnTopHint)
        self.assertTrue(flags & Qt.WindowType.Tool)

    def test_translucent_background_attribute(self) -> None:
        """Verify WA_TranslucentBackground attribute is enabled."""
        window = FramelessWindow()
        self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))

    def test_main_window_properties(self) -> None:
        """Verify MainWindow default properties (title, dimensions)."""
        window = MainWindow()
        self.assertEqual(window.windowTitle(), "MediaDock")
        self.assertEqual(window.width(), 360)
        self.assertEqual(window.height(), 140)

    def test_artwork_label_dimensions(self) -> None:
        """Verify art_label fixed dimensions (72x72) and default pixmap match."""
        window = MainWindow()
        self.assertEqual(window.art_label.width(), 72)
        self.assertEqual(window.art_label.height(), 72)
        self.assertEqual(window._default_art_pixmap.width(), 72)
        self.assertEqual(window._default_art_pixmap.height(), 72)

    def test_close_event_hides_window_when_close_to_tray_enabled(self) -> None:
        """Verify closeEvent ignores close and calls hide() when close_to_tray setting is True."""
        from unittest.mock import MagicMock
        from PySide6.QtGui import QCloseEvent
        from src.core.settings import SettingsManager

        mock_settings = MagicMock(spec=SettingsManager)
        mock_settings.get_close_to_tray.return_value = True
        mock_settings.get_always_on_top.return_value = True
        mock_settings.get_compact_mode.return_value = False
        mock_settings.get_window_position.return_value = (100, 100)

        window = MainWindow(settings_manager=mock_settings)
        window.show()

        event = QCloseEvent()
        window.closeEvent(event)

        self.assertFalse(event.isAccepted())
        self.assertFalse(window.isVisible())

    def test_close_event_quits_app_when_close_to_tray_disabled(self) -> None:
        """Verify closeEvent accepts event and calls QApplication.quit when close_to_tray is False."""
        from unittest.mock import MagicMock, patch
        from PySide6.QtGui import QCloseEvent
        from src.core.settings import SettingsManager

        mock_settings = MagicMock(spec=SettingsManager)
        mock_settings.get_close_to_tray.return_value = False
        mock_settings.get_always_on_top.return_value = True
        mock_settings.get_compact_mode.return_value = False
        mock_settings.get_window_position.return_value = (100, 100)

        window = MainWindow(settings_manager=mock_settings)

        event = QCloseEvent()
        with patch.object(QApplication, "quit") as mock_quit:
            window.closeEvent(event)
            self.assertTrue(event.isAccepted())
            mock_quit.assert_called_once()

    def test_toggle_window_visibility_logic(self) -> None:
        """Verify showing and hiding window toggles isVisible state cleanly."""
        window = MainWindow()

        window.show()
        self.assertTrue(window.isVisible())

        window.hide()
        self.assertFalse(window.isVisible())

        window.show()
        self.assertTrue(window.isVisible())


if __name__ == "__main__":
    unittest.main()
