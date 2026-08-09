"""Windows Global Hotkey Manager for MediaDock using Win32 API and PySide6 native event filtering."""

import sys
import logging
import ctypes
from typing import Optional, Set, Callable, Tuple
from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter, QCoreApplication

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from ctypes import wintypes

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", wintypes.POINT),
        ]

# Win32 Hotkey Constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000

VK_M = 0x4D
VK_SPACE = 0x20

HOTKEY_ID_SHOW_HIDE = 1
HOTKEY_ID_PLAY_PAUSE = 2


class HotkeyNativeEventFilter(QAbstractNativeEventFilter):
    """Native event filter intercepting WM_HOTKEY messages from Qt event loop."""

    def __init__(self, callback: Callable[[int], None]) -> None:
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type: bytes, message: int) -> Tuple[bool, int]:
        """Intercept WM_HOTKEY (0x0312) messages and notify callback with hotkey ID."""
        if IS_WINDOWS and message and (event_type == b"windows_generic_MSG" or event_type.startswith(b"windows_")):
            try:
                msg = MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    hotkey_id = int(msg.wParam)
                    self._callback(hotkey_id)
                    return True, 0
            except Exception as e:
                logger.error("Error decoding WM_HOTKEY message in native event filter: %s", e)
        return False, 0



class GlobalHotkeyManager(QObject):
    """Manages OS-wide global keyboard shortcuts using Win32 RegisterHotKey and PySide6 native event filtering."""

    show_hide_requested = Signal()
    play_pause_requested = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._registered_ids: Set[int] = set()
        self._event_filter: Optional[HotkeyNativeEventFilter] = None
        self._is_started: bool = False

    @property
    def is_started(self) -> bool:
        """Return True if hotkey manager is currently active."""
        return self._is_started

    def is_registered(self, hotkey_id: int) -> bool:
        """Return True if specific hotkey ID is currently registered with Windows OS."""
        return hotkey_id in self._registered_ids

    def start(self) -> bool:
        """Register global hotkeys and install native event filter into QApplication."""
        if not IS_WINDOWS:
            logger.info("Global hotkeys disabled: Non-Windows platform (%s).", sys.platform)
            return False

        if self._is_started:
            return True

        app = QCoreApplication.instance()
        if app is not None and self._event_filter is None:
            self._event_filter = HotkeyNativeEventFilter(self._on_hotkey_triggered)
            app.installNativeEventFilter(self._event_filter)

        # Register Shortcut 1: Ctrl + Alt + M -> Show/Hide
        self._register_single_hotkey(
            HOTKEY_ID_SHOW_HIDE,
            MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
            VK_M,
            "Ctrl+Alt+M (Show/Hide MediaDock)",
        )

        # Register Shortcut 2: Ctrl + Alt + Space -> Play/Pause
        self._register_single_hotkey(
            HOTKEY_ID_PLAY_PAUSE,
            MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
            VK_SPACE,
            "Ctrl+Alt+Space (Toggle Play/Pause)",
        )

        self._is_started = True
        return len(self._registered_ids) > 0

    def _register_single_hotkey(
        self, hotkey_id: int, modifiers: int, vk_code: int, label: str
    ) -> bool:
        """Helper to register a single hotkey ID via win32 RegisterHotKey."""
        user32 = getattr(ctypes.windll, "user32", None)
        if user32 is None:
            return False

        try:
            res = user32.RegisterHotKey(None, hotkey_id, modifiers, vk_code)
            if res != 0:
                self._registered_ids.add(hotkey_id)
                logger.info("Successfully registered global hotkey: %s", label)
                return True
            else:
                logger.warning(
                    "Failed to register global hotkey (ID %d: %s). Key combination may be in use.",
                    hotkey_id,
                    label,
                )
                return False
        except Exception as e:
            logger.error("Error registering global hotkey %s: %s", label, e)
            return False

    def stop(self) -> None:
        """Unregister all active hotkeys and remove native event filter. Safe to call multiple times."""
        user32 = getattr(getattr(ctypes, "windll", None), "user32", None)

        if user32 is not None and self._registered_ids:
            for hotkey_id in list(self._registered_ids):
                try:
                    user32.UnregisterHotKey(None, hotkey_id)
                except Exception as e:
                    logger.error("Error unregistering hotkey ID %d: %s", hotkey_id, e)
            self._registered_ids.clear()

        app = QCoreApplication.instance()
        if app is not None and self._event_filter is not None:
            try:
                app.removeNativeEventFilter(self._event_filter)
            except Exception as e:
                logger.error("Error removing native event filter: %s", e)
            self._event_filter = None

        self._is_started = False

    def _on_hotkey_triggered(self, hotkey_id: int) -> None:
        """Dispatch Qt signals based on triggered hotkey ID."""
        if hotkey_id == HOTKEY_ID_SHOW_HIDE:
            self.show_hide_requested.emit()
        elif hotkey_id == HOTKEY_ID_PLAY_PAUSE:
            self.play_pause_requested.emit()
