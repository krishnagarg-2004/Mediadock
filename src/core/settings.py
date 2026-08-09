"""Settings manager for MediaDock application preferences using Qt-native QSettings."""

from typing import Any, Optional, Tuple
from PySide6.QtCore import QObject, QSettings, Signal


def _to_bool(value: Any, default: bool) -> bool:
    """Convert QSettings value to explicit bool, handling string/int conversions safely."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(value, int):
        return bool(value)
    return default


def _to_int(value: Any, default: int) -> int:
    """Convert QSettings value to explicit int safely."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class SettingsManager(QObject):
    """Decoupled settings manager wrapping QSettings with typed accessors and signals."""

    settings_changed = Signal(str, object)

    # Approved Default Values
    DEFAULTS = {
        "general/close_to_tray": True,
        "general/start_hidden": False,
        "window/always_on_top": True,
        "window/remember_position": True,
        "window/pos_x": -1,
        "window/pos_y": -1,
    }

    def __init__(
        self,
        qsettings: Optional[QSettings] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        if qsettings is not None:
            self._settings = qsettings
        else:
            self._settings = QSettings("KrishnaOS", "MediaDock")

    # --- Generic Getter & Setter ---

    def get(self, key: str) -> Any:
        """Retrieve setting value by key with typed default fallback."""
        default = self.DEFAULTS.get(key, None)
        raw_val = self._settings.value(key, default)

        if isinstance(default, bool):
            return _to_bool(raw_val, default)
        if isinstance(default, int):
            return _to_int(raw_val, default)
        return raw_val

    def set(self, key: str, value: Any) -> None:
        """Store setting value by key and emit settings_changed signal if value changed."""
        old_val = self.get(key)
        self._settings.setValue(key, value)
        new_val = self.get(key)

        if old_val != new_val:
            self.settings_changed.emit(key, new_val)

    # --- Typed Accessors ---

    def get_close_to_tray(self) -> bool:
        """Return whether closing main window hides to system tray."""
        return self.get("general/close_to_tray")

    def set_close_to_tray(self, enabled: bool) -> None:
        """Set whether closing main window hides to system tray."""
        self.set("general/close_to_tray", bool(enabled))

    def get_start_hidden(self) -> bool:
        """Return whether application starts minimized/hidden in system tray."""
        return self.get("general/start_hidden")

    def set_start_hidden(self, hidden: bool) -> None:
        """Set whether application starts minimized/hidden in system tray."""
        self.set("general/start_hidden", bool(hidden))

    def get_always_on_top(self) -> bool:
        """Return whether main window stays always on top of other windows."""
        return self.get("window/always_on_top")

    def set_always_on_top(self, on_top: bool) -> None:
        """Set whether main window stays always on top."""
        self.set("window/always_on_top", bool(on_top))

    def get_remember_position(self) -> bool:
        """Return whether window screen position is saved and restored."""
        return self.get("window/remember_position")

    def set_remember_position(self, remember: bool) -> None:
        """Set whether window screen position is saved and restored."""
        self.set("window/remember_position", bool(remember))

    def get_window_position(self) -> Tuple[int, int]:
        """Return saved (pos_x, pos_y) coordinate tuple (-1, -1 if unset)."""
        x = self.get("window/pos_x")
        y = self.get("window/pos_y")
        return (x, y)

    def set_window_position(self, x: int, y: int) -> None:
        """Save window screen position (x, y) coordinates."""
        self.set("window/pos_x", int(x))
        self.set("window/pos_y", int(y))

    def clear(self) -> None:
        """Reset all stored settings in the QSettings store."""
        self._settings.clear()
