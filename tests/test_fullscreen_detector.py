"""Unit tests for Windows Fullscreen Game and Application Detector."""

import unittest
from unittest.mock import patch

from src.core.fullscreen_detector import is_foreground_fullscreen


class TestFullscreenDetector(unittest.TestCase):
    @patch("ctypes.windll.user32.MonitorFromWindow")
    @patch("ctypes.windll.user32.GetWindowRect")
    @patch("ctypes.windll.user32.GetWindowLongW")
    @patch("ctypes.windll.user32.IsZoomed")
    @patch("ctypes.windll.user32.GetClassNameW")
    @patch("ctypes.windll.user32.GetForegroundWindow")
    def test_fullscreen_window_detected(
        self, mock_hwnd, mock_class, mock_zoomed, mock_style, mock_rect, mock_monitor
    ):
        mock_hwnd.return_value = 12345
        mock_class.return_value = 1
        mock_zoomed.return_value = 0  # Not a standard maximized window
        mock_style.return_value = 0x80000000  # WS_POPUP borderless fullscreen (no WS_CAPTION)
        mock_monitor.return_value = 0  # Force fallback to explicit screen_rect in unit test

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

    @patch("ctypes.windll.user32.IsZoomed")
    @patch("ctypes.windll.user32.GetClassNameW")
    @patch("ctypes.windll.user32.GetForegroundWindow")
    def test_maximized_desktop_app_never_triggers_fullscreen(
        self, mock_hwnd, mock_class, mock_zoomed
    ):
        mock_hwnd.return_value = 12345
        mock_class.return_value = 1
        mock_zoomed.return_value = 1  # Normal maximized window (Chrome, Spotify, IDE)
        self.assertFalse(is_foreground_fullscreen((0, 0, 1536, 960), ignore_hwnd=99999))

    @patch("ctypes.windll.user32.GetWindowLongW")
    @patch("ctypes.windll.user32.IsZoomed")
    @patch("ctypes.windll.user32.GetClassNameW")
    @patch("ctypes.windll.user32.GetForegroundWindow")
    def test_window_with_caption_never_triggers_fullscreen(
        self, mock_hwnd, mock_class, mock_zoomed, mock_style
    ):
        mock_hwnd.return_value = 12345
        mock_class.return_value = 1
        mock_zoomed.return_value = 0
        mock_style.return_value = 0x00CF0000  # WS_OVERLAPPEDWINDOW includes WS_CAPTION
        self.assertFalse(is_foreground_fullscreen((0, 0, 1536, 960), ignore_hwnd=99999))

    @patch("ctypes.windll.user32.GetForegroundWindow")
    def test_null_or_ignored_hwnd_returns_false(self, mock_hwnd):
        mock_hwnd.return_value = 0
        self.assertFalse(is_foreground_fullscreen((0, 0, 1920, 1080)))

        mock_hwnd.return_value = 55555
        self.assertFalse(is_foreground_fullscreen((0, 0, 1920, 1080), ignore_hwnd=55555))


if __name__ == "__main__":
    unittest.main()
