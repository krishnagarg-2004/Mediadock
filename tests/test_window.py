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



if __name__ == "__main__":
    unittest.main()
