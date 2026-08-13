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
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VK_M = 0x4D
VK_SPACE = 0x20

HOTKEY_ID_SHOW_HIDE = 1
HOTKEY_ID_PLAY_PAUSE = 2

NAMED_VK_MAP = {
    "space": 0x20,
    "spacebar": 0x20,
    "tab": 0x09,
    "return": 0x0D,
    "enter": 0x0D,
    "escape": 0x1B,
    "esc": 0x1B,
    "pageup": 0x21,
    "pgup": 0x21,
    "pagedown": 0x22,
    "pgdn": 0x22,
    "end": 0x23,
    "home": 0x24,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "insert": 0x2D,
    "delete": 0x2E,
    "del": 0x2E,
}

# Populate F1-F24 keys
for _i in range(1, 25):
    NAMED_VK_MAP[f"f{_i}"] = 0x70 + (_i - 1)


def parse_key_sequence(sequence_str: str) -> Tuple[int, int]:
    """Parse a Qt-style key sequence string (e.g. 'Ctrl+Alt+M') into Win32 (modifiers, vk_code).

    Raises ValueError if sequence is malformed, missing modifiers, or contains invalid keys.
    """
    if not sequence_str or not isinstance(sequence_str, str):
        raise ValueError("Hotkey sequence must be a non-empty string.")

    tokens = [t.strip() for t in sequence_str.split("+") if t.strip()]
    if not tokens:
        raise ValueError("Invalid hotkey sequence.")

    modifiers = 0
    vk_code = 0

    for token in tokens:
        lower = token.lower()
        if lower in ("ctrl", "control"):
            modifiers |= MOD_CONTROL
        elif lower in ("alt", "menu"):
            modifiers |= MOD_ALT
        elif lower == "shift":
            modifiers |= MOD_SHIFT
        elif lower in ("win", "meta", "super", "cmd"):
            modifiers |= MOD_WIN
        else:
            if vk_code != 0:
                raise ValueError(f"Multiple main keys in sequence '{sequence_str}'.")

            if lower in NAMED_VK_MAP:
                vk_code = NAMED_VK_MAP[lower]
            elif len(token) == 1:
                ch = token.upper()
                if "A" <= ch <= "Z" or "0" <= ch <= "9":
                    vk_code = ord(ch)
                else:
                    raise ValueError(f"Unsupported character key '{token}' in sequence.")
            else:
                raise ValueError(f"Unknown key token '{token}' in sequence.")

    if modifiers == 0:
        raise ValueError(f"Hotkey sequence '{sequence_str}' must contain at least one modifier key (Ctrl, Alt, Shift, Win).")

    if vk_code == 0:
        raise ValueError(f"Hotkey sequence '{sequence_str}' missing main key.")

    return modifiers, vk_code


class HotkeyNativeEventFilter(QAbstractNativeEventFilter):
    """Native event filter intercepting WM_HOTKEY messages from Qt event loop."""

    def __init__(self, callback: Callable[[int], None]) -> None:
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type: bytes, message: int) -> Tuple[bool, int]:
        """Intercept WM_HOTKEY (0x0312) messages and notify callback with hotkey ID."""
        if IS_WINDOWS and message is not None:
            try:
                addr = int(message)
                msg = MSG.from_address(addr)
                if msg.message == WM_HOTKEY:
                    logger.info("WM_HOTKEY intercepted in native event filter: ID=%d", msg.wParam)
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
        self._show_hide_seq: str = "Ctrl+Alt+S"
        self._play_pause_seq: str = "Ctrl+Alt+Space"
        self._target_hwnd: Optional[int] = None

    @property
    def is_started(self) -> bool:
        """Return True if hotkey manager is currently active."""
        return self._is_started

    def set_target_hwnd(self, hwnd: Optional[int]) -> None:
        """Set target window HWND to receive Win32 WM_HOTKEY messages."""
        self._target_hwnd = hwnd

    def is_registered(self, hotkey_id: int) -> bool:
        """Return True if specific hotkey ID is currently registered with Windows OS."""
        return hotkey_id in self._registered_ids

    def get_show_hide_sequence(self) -> str:
        """Return current Show/Hide hotkey sequence string."""
        return self._show_hide_seq

    def get_play_pause_sequence(self) -> str:
        """Return current Play/Pause hotkey sequence string."""
        return self._play_pause_seq

    def start(
        self,
        show_hide_seq: str = "Ctrl+Alt+S",
        play_pause_seq: str = "Ctrl+Alt+Space",
        target_hwnd: Optional[int] = None,
    ) -> bool:
        """Register global hotkeys and install native event filter into QApplication."""
        if not IS_WINDOWS:
            logger.info("Global hotkeys disabled: Non-Windows platform (%s).", sys.platform)
            return False

        if target_hwnd is not None:
            self._target_hwnd = target_hwnd

        if self._is_started:
            return True

        app = QCoreApplication.instance()
        if app is not None and self._event_filter is None:
            self._event_filter = HotkeyNativeEventFilter(self._on_hotkey_triggered)
            app.installNativeEventFilter(self._event_filter)

        self._show_hide_seq = show_hide_seq
        self._play_pause_seq = play_pause_seq

        self._register_configured_hotkeys()

        self._is_started = True
        return len(self._registered_ids) > 0

    def _register_configured_hotkeys(self) -> bool:
        """Register configured Show/Hide and Play/Pause hotkeys."""
        ok_sh = False
        ok_pp = False

        try:
            mod_sh, vk_sh = parse_key_sequence(self._show_hide_seq)
            ok_sh = self._register_single_hotkey(
                HOTKEY_ID_SHOW_HIDE,
                mod_sh | MOD_NOREPEAT,
                vk_sh,
                f"{self._show_hide_seq} (Show/Hide MediaDock)",
            )
        except Exception as e:
            logger.error("Failed to parse Show/Hide hotkey sequence '%s': %s", self._show_hide_seq, e)

        try:
            mod_pp, vk_pp = parse_key_sequence(self._play_pause_seq)
            ok_pp = self._register_single_hotkey(
                HOTKEY_ID_PLAY_PAUSE,
                mod_pp | MOD_NOREPEAT,
                vk_pp,
                f"{self._play_pause_seq} (Toggle Play/Pause)",
            )
        except Exception as e:
            logger.error("Failed to parse Play/Pause hotkey sequence '%s': %s", self._play_pause_seq, e)

        return ok_sh and ok_pp

    def rebind_hotkeys(self, show_hide_seq: str, play_pause_seq: str) -> bool:
        """Safely update hotkey bindings. Rollback to previous working shortcuts if registration fails."""
        # 1. Validate both sequences before modifying active bindings
        try:
            mod_sh, vk_sh = parse_key_sequence(show_hide_seq)
            mod_pp, vk_pp = parse_key_sequence(play_pause_seq)
        except ValueError as e:
            logger.warning("Hotkey rebind validation failed: %s", e)
            return False

        # Reject duplicate shortcuts assigned to both actions
        if (mod_sh, vk_sh) == (mod_pp, vk_pp):
            logger.warning("Hotkey rebind failed: Duplicate shortcuts assigned to both actions.")
            return False

        old_sh_seq = self._show_hide_seq
        old_pp_seq = self._play_pause_seq

        # 2. Unregister current hotkeys
        self._unregister_hotkey_ids()

        # 3. Attempt registering new hotkeys
        self._show_hide_seq = show_hide_seq
        self._play_pause_seq = play_pause_seq

        ok_sh = self._register_single_hotkey(
            HOTKEY_ID_SHOW_HIDE,
            mod_sh | MOD_NOREPEAT,
            vk_sh,
            f"{show_hide_seq} (Show/Hide MediaDock)",
        )
        ok_pp = self._register_single_hotkey(
            HOTKEY_ID_PLAY_PAUSE,
            mod_pp | MOD_NOREPEAT,
            vk_pp,
            f"{play_pause_seq} (Toggle Play/Pause)",
        )

        # 4. If both succeed, return True
        if ok_sh and ok_pp:
            logger.info("Successfully rebound hotkeys to '%s' and '%s'.", show_hide_seq, play_pause_seq)
            return True

        # 5. Rollback on failure
        logger.warning("Hotkey registration failed (Show/Hide ok=%s, Play/Pause ok=%s). Rolling back to '%s' and '%s'.", ok_sh, ok_pp, old_sh_seq, old_pp_seq)
        self._unregister_hotkey_ids()

        self._show_hide_seq = old_sh_seq
        self._play_pause_seq = old_pp_seq

        try:
            self._register_configured_hotkeys()
        except Exception as e:
            logger.error("Error during hotkey rollback restoration: %s", e)

        return False

    def _register_single_hotkey(
        self, hotkey_id: int, modifiers: int, vk_code: int, label: str
    ) -> bool:
        """Helper to register a single hotkey ID via win32 RegisterHotKey."""
        user32 = getattr(ctypes.windll, "user32", None)
        if user32 is None:
            return False

        target = ctypes.wintypes.HWND(self._target_hwnd) if self._target_hwnd else None
        try:
            res = user32.RegisterHotKey(target, hotkey_id, modifiers, vk_code)
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

    def _unregister_hotkey_ids(self) -> None:
        """Helper to unregister all registered Win32 hotkey IDs."""
        user32 = getattr(getattr(ctypes, "windll", None), "user32", None)
        if user32 is not None and self._registered_ids:
            target = ctypes.wintypes.HWND(self._target_hwnd) if self._target_hwnd else None
            for hotkey_id in list(self._registered_ids):
                try:
                    user32.UnregisterHotKey(target, hotkey_id)
                except Exception as e:
                    logger.error("Error unregistering hotkey ID %d: %s", hotkey_id, e)
            self._registered_ids.clear()

    def stop(self) -> None:
        """Unregister all active hotkeys and remove native event filter. Safe to call multiple times."""
        self._unregister_hotkey_ids()

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
