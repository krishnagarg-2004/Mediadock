"""Windows Fullscreen Application & Game Detector using Win32 API."""

import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

GWL_STYLE = -16
WS_CAPTION = 0x00C00000
MONITOR_DEFAULTTONEAREST = 2

_SHELL_WINDOW_CLASSES = frozenset({
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "NotifyIconOverflowWindow",
    "TaskListThumbnailWnd",
})


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def is_foreground_fullscreen(
    screen_rect: Tuple[int, int, int, int],
    ignore_hwnd: Optional[int] = None,
) -> bool:
    """Check if the foreground window is an exclusive/borderless fullscreen app covering the monitor.

    Explicitly excludes normal maximized desktop applications (Chrome, Spotify, IDEs, Explorer)
    by verifying IsZoomed == 0, absence of standard WS_CAPTION frame, and comparing physical
    Win32 window bounds against the monitor's Win32 rcMonitor coordinates.
    """
    if sys.platform != "win32":
        return False

    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd or hwnd == ignore_hwnd:
            return False

        # Ignore desktop / taskbar shell windows
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        if class_buf.value in _SHELL_WINDOW_CLASSES:
            return False

        # Never hide for standard maximized desktop applications (Spotify, browsers, IDEs)
        if user32.IsZoomed(hwnd):
            return False

        # Never hide for standard windowed/framed applications carrying a caption bar
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        if (style & WS_CAPTION) == WS_CAPTION:
            return False

        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False

        # Prefer Win32 physical monitor bounds in the exact same coordinate space as GetWindowRect
        m_left, m_top, m_right, m_bottom = (
            screen_rect[0],
            screen_rect[1],
            screen_rect[0] + screen_rect[2],
            screen_rect[1] + screen_rect[3],
        )
        hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if hmon:
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                m_left = mi.rcMonitor.left
                m_top = mi.rcMonitor.top
                m_right = mi.rcMonitor.right
                m_bottom = mi.rcMonitor.bottom

        if m_right <= m_left or m_bottom <= m_top:
            return False

        # True borderless/exclusive fullscreen covers the full monitor rect (allow 1px rounding margin)
        if (
            rect.left <= m_left + 1
            and rect.top <= m_top + 1
            and rect.right >= m_right - 1
            and rect.bottom >= m_bottom - 1
        ):
            return True

        return False
    except Exception:
        return False
