"""Unit tests for InteractiveScrubSlider component."""

import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent

from src.ui.components import InteractiveScrubSlider

app = QApplication.instance() or QApplication([])


class TestInteractiveScrubSlider(unittest.TestCase):
    def setUp(self):
        self.slider = InteractiveScrubSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 10000)
        self.slider.resize(200, 20)

    def tearDown(self):
        self.slider.deleteLater()

    def test_default_time_formatter(self):
        self.assertEqual(InteractiveScrubSlider._default_time_format(0), "00:00")
        self.assertEqual(InteractiveScrubSlider._default_time_format(65000), "01:05")
        self.assertEqual(InteractiveScrubSlider._default_time_format(3600000), "60:00")

    def test_mouse_press_sets_proportional_value(self):
        # Click at 50% width (x = 100 of 200)
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(100.0, 10.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.slider.mousePressEvent(press_event)
        self.assertAlmostEqual(self.slider.value(), 5000, delta=100)

    def test_mouse_move_updates_tooltip(self):
        # Hover at 25% width (x = 50 of 200 -> 2500 ms -> 00:02)
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(50.0, 10.0),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.slider.mouseMoveEvent(move_event)
        self.assertEqual(self.slider.toolTip(), "00:02")


if __name__ == "__main__":
    unittest.main()
