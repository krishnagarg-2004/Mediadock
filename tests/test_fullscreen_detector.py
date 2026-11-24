"""Unit tests for Windows Fullscreen Game and Application Detector."""

import unittest
from unittest.mock import patch, MagicMock
import ctypes

from src.core.fullscreen_detector import is_foreground_fullscreen, RECT


class TestFullscreenDetector(unittest.TestCase):
    @patch("ctypes.windll.user32.GetForegroundWindow")
    @patch("ctypes.windll.user32.GetClassNameW")
    @patch("ctypes.windll.user32.GetWindowRect")
    def test_fullscreen_window_detected(self, mock_rect, mock_class, mock_hwnd):
        mock_hwnd.return_value = 12345
        mock_class.return_value = 1
        
        # Window rect exactly covers screen 0, 0, 1920, 1080
        def fill_rect(hwnd, rect_ptr):
            rect = rect_ptr._obj
            rect.left = 0
            rect.top = 0
            rect.right = 1920
            rect.bottom = 1080
            return 1

        mock_rect.side_effect = fill_rect
        is_fs = is_foreground_fullscreen((0, 0, 1920, 1080), ignore_hwnd=99999)
        self.assertTrue(is_fs)

    @patch("ctypes.windll.user32.GetForegroundWindow")
    def test_null_or_ignored_hwnd_returns_false(self, mock_hwnd):
        mock_hwnd.return_value = 0
        self.assertFalse(is_foreground_fullscreen((0, 0, 1920, 1080)))

        mock_hwnd.return_value = 55555
        self.assertFalse(is_foreground_fullscreen((0, 0, 1920, 1080), ignore_hwnd=55555))


if __name__ == "__main__":
    unittest.main()
