"""Unit tests for InteractiveScrubSlider component."""

import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent, QWheelEvent, QColor
from PySide6.QtCore import QPoint

from src.ui.components import InteractiveScrubSlider, VolumeWedgeWidget

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


class TestVolumeWedgeWidget(unittest.TestCase):
    """Unit tests for VLC-style triangular wedge volume slider."""

    def setUp(self):
        self.wedge = VolumeWedgeWidget(initial_value=50, wedge_width=60, wedge_height=16)

    def tearDown(self):
        self.wedge.deleteLater()

    def test_initial_value_and_clamping(self):
        self.assertEqual(self.wedge.value(), 50)
        self.wedge.setValue(150)
        self.assertEqual(self.wedge.value(), 100)
        self.wedge.setValue(-20)
        self.assertEqual(self.wedge.value(), 0)

    def test_click_sets_proportional_volume(self):
        # Click near middle (e.g. x = 32 of 64 total width)
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(32.0, 8.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.wedge.mousePressEvent(press_event)
        self.assertAlmostEqual(self.wedge.value(), 50, delta=5)

    def test_drag_emits_value_changed(self):
        emitted_values = []
        self.wedge.valueChanged.connect(lambda v: emitted_values.append(v))

        # Drag from left to 75% position
        press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(2.0, 8.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.wedge.mousePressEvent(press)

        move = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(47.0, 8.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.wedge.mouseMoveEvent(move)
        self.assertTrue(len(emitted_values) >= 2)
        self.assertAlmostEqual(self.wedge.value(), 75, delta=5)

    def test_wheel_event_adjusts_volume_like_vlc(self):
        self.wedge.setValue(50)
        # Scroll up (+120 delta) -> +5%
        wheel_up = QWheelEvent(
            QPointF(30.0, 8.0),
            QPointF(30.0, 8.0),
            QPoint(0, 0),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        self.wedge.wheelEvent(wheel_up)
        self.assertEqual(self.wedge.value(), 55)

        # Scroll down (-120 delta) -> -5%
        wheel_down = QWheelEvent(
            QPointF(30.0, 8.0),
            QPointF(30.0, 8.0),
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        self.wedge.wheelEvent(wheel_down)
        self.assertEqual(self.wedge.value(), 50)

    def test_mute_state_and_tooltip(self):
        self.wedge.setValue(80)
        self.assertFalse(self.wedge.is_muted())
        self.assertIn("80%", self.wedge.toolTip())

        self.wedge.set_muted(True)
        self.assertTrue(self.wedge.is_muted())
        self.assertIn("Muted", self.wedge.toolTip())

    def test_dynamic_accent_color_adaptation(self):
        # Set vibrant magenta accent color
        self.wedge.set_accent_color(QColor("#E056FD"))
        self.assertEqual(self.wedge._accent_color, QColor("#E056FD"))
        # Right click toggles mute
        right_click = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(30.0, 8.0),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
        toggles = []
        self.wedge.muteToggled.connect(lambda m: toggles.append(m))
        self.wedge.mousePressEvent(right_click)
        self.assertTrue(self.wedge.is_muted())
        self.assertEqual(toggles, [True])


if __name__ == "__main__":
    unittest.main()
