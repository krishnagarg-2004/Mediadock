"""Windows Fullscreen Application & Game Detector using Win32 API."""

import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def is_foreground_fullscreen(
    screen_rect: Tuple[int, int, int, int],
    ignore_hwnd: Optional[int] = None,
) -> bool:
    """Check if the current foreground window is running in fullscreen covering screen_rect.

    Args:
        screen_rect: Tuple of (x, y, width, height) of the screen to check.
        ignore_hwnd: Optional HWND of MediaDock window to ignore.

    Returns:
        True if an active application or game is running in borderless or exclusive fullscreen.
    """
    if sys.platform != "win32":
        return False

    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd or hwnd == ignore_hwnd:
            return False

        # Ignore desktop shell windows
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        class_name = class_buf.value
        if class_name in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
            return False

        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False

        sx, sy, sw, sh = screen_rect
        s_right = sx + sw
        s_bottom = sy + sh

        # Check if window covers or exceeds the screen boundaries
        if rect.left <= sx and rect.top <= sy and rect.right >= s_right and rect.bottom >= s_bottom:
            return True

        return False
    except Exception:
        return False
