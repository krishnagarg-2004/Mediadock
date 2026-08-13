"""Unit tests for src/ui/theme.py UI design tokens and Qt-only color extraction."""

import sys
import unittest
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from src.core.models import PlaybackStatus
from src.ui.theme import (
    COLOR_BG_BASE,
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GREEN,
    extract_dominant_color,
    get_status_badge_style,
    get_button_stylesheet,
    get_slider_stylesheet,
)


class TestUITheme(unittest.TestCase):
    """Test suite for UI design tokens, status badge styling, and Qt-only color extraction."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a QApplication instance exists for QImage testing."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_design_tokens_validity(self) -> None:
        """Verify color tokens are valid QColor objects."""
        self.assertTrue(COLOR_BG_BASE.isValid())
        self.assertTrue(COLOR_ACCENT_BLUE.isValid())
        self.assertEqual(COLOR_BG_BASE.name(), "#000000")

    def test_extract_dominant_color_none_returns_fallback(self) -> None:
        """Verify None image bytes returns default fallback accent color."""
        result = extract_dominant_color(None, fallback=COLOR_ACCENT_GREEN)
        self.assertEqual(result, COLOR_ACCENT_GREEN)

    def test_extract_dominant_color_invalid_bytes_returns_fallback(self) -> None:
        """Verify invalid image bytes returns fallback color."""
        result = extract_dominant_color(b"invalid_image_bytes", fallback=COLOR_ACCENT_BLUE)
        self.assertEqual(result, COLOR_ACCENT_BLUE)

    def test_extract_dominant_color_valid_image(self) -> None:
        """Verify extract_dominant_color extracts color from valid PNG bytes using Qt only."""
        # Create a solid green QImage and convert to PNG bytes
        img = QImage(32, 32, QImage.Format.Format_RGB32)
        img.fill(QColor(40, 180, 80))  # Vivid green

        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buffer, "PNG")
        art_bytes = bytes(ba)

        extracted = extract_dominant_color(art_bytes, fallback=COLOR_ACCENT_BLUE)
        self.assertTrue(extracted.isValid())
        # Extracted green channel should be dominant
        r, g, b, _ = extracted.getRgb()
        self.assertGreater(g, r)
        self.assertGreater(g, b)

    def test_status_badge_style(self) -> None:
        """Verify get_status_badge_style returns correct tuple format."""
        playing_text, text_hex, bg_hex = get_status_badge_style(PlaybackStatus.PLAYING)
        self.assertEqual(playing_text, "PLAYING")
        self.assertEqual(text_hex, "#00FF7F")
        self.assertEqual(bg_hex, "#0A2919")

        paused_text, p_text_hex, p_bg_hex = get_status_badge_style(PlaybackStatus.PAUSED)
        self.assertEqual(paused_text, "PAUSED")
        self.assertEqual(p_text_hex, "#C1121C")

    def test_stylesheet_generators(self) -> None:
        """Verify get_button_stylesheet and get_slider_stylesheet produce valid QSS strings."""
        btn_qss = get_button_stylesheet()
        self.assertIn("QPushButton", btn_qss)
        self.assertIn("#222222", btn_qss)

        slider_qss = get_slider_stylesheet(QColor("#00FF7F"))
        self.assertIn("QSlider::groove:horizontal", slider_qss)
        self.assertIn("#00ff7f", slider_qss)


if __name__ == "__main__":
    unittest.main()
