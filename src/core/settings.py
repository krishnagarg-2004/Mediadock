"""Settings manager for MediaDock application preferences using Qt-native QSettings."""

from typing import Any, Optional, Tuple
from PySide6.QtCore import QObject, QSettings, Signal

from src.utils.autostart import AutostartManager


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


def _to_float(value: Any, default: float) -> float:
    """Convert QSettings value to explicit float safely."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class SettingsManager(QObject):
    """Decoupled settings manager wrapping QSettings with typed accessors and signals."""

    settings_changed = Signal(str, object)

    # Approved Default Values
    DEFAULTS = {
        "general/close_to_tray": True,
        "general/start_hidden": False,
        "general/autostart_windows": False,
        "window/always_on_top": True,
        "window/compact_mode": False,
        "dynamic_island/enabled": True,
        "dynamic_island/collapse_delay_ms": 3500,
        "hotkeys/show_hide": "Ctrl+Alt+S",
        "hotkeys/play_pause": "Ctrl+Alt+Space",
        "audio/preamp_boost_db": 0.0,
        "audio/bass_db": 0.0,
        "audio/clarity_db": 0.0,
        "audio/treble_db": 0.0,
        "audio/noise_gate_percent": 5,
        "audio/eq_preset": "Flat",
        "audio/eq_band_60": 0.0,
        "audio/eq_band_250": 0.0,
        "audio/eq_band_1000": 0.0,
        "audio/eq_band_4000": 0.0,
        "audio/eq_band_16000": 0.0,
        "audio/eq_enabled": True,
        "dynamic_island/expand_trigger": "hover",
        "dynamic_island/hover_intent_delay_ms": 0,
        "window/fullscreen_auto_hide": False,
        "window/display_monitor": "primary",
        "audio/spectrum_mode": "rms",
        "features/lyrics_enabled": True,
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
        if isinstance(default, float):
            return _to_float(raw_val, default)
        return raw_val

    def set(self, key: str, value: Any) -> None:
        """Store setting value by key and emit settings_changed signal if value changed."""
        old_val = self.get(key)
        self._settings.setValue(key, value)
        self._settings.sync()
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

    def get_autostart_windows(self) -> bool:
        """Return whether autostart with Windows is enabled."""
        return self.get("general/autostart_windows")

    def set_autostart_windows(self, enabled: bool) -> bool:
        """Set whether autostart with Windows is enabled and synchronize with Windows Registry."""
        if enabled:
            success = AutostartManager.enable_autostart()
        else:
            success = AutostartManager.disable_autostart()

        self.set("general/autostart_windows", bool(enabled))
        return success

    def get_always_on_top(self) -> bool:
        """Return whether main window stays always on top of other windows."""
        return self.get("window/always_on_top")

    def set_always_on_top(self, on_top: bool) -> None:
        """Set whether main window stays always on top."""
        self.set("window/always_on_top", bool(on_top))

    def get_compact_mode(self) -> bool:
        """Deprecated legacy accessor. Kept for backward compatibility."""
        return self.get("window/compact_mode")

    def set_compact_mode(self, enabled: bool) -> None:
        """Deprecated legacy accessor. Kept for backward compatibility."""
        self.set("window/compact_mode", bool(enabled))

    def get_dynamic_island_enabled(self) -> bool:
        """Return whether Dynamic Island desktop overlay is enabled."""
        return self.get("dynamic_island/enabled")

    def set_dynamic_island_enabled(self, enabled: bool) -> None:
        """Set whether Dynamic Island desktop overlay is enabled."""
        self.set("dynamic_island/enabled", bool(enabled))

    def get_collapse_delay_ms(self) -> int:
        """Return auto-collapse inactivity delay in milliseconds (default 3500 ms)."""
        return self.get("dynamic_island/collapse_delay_ms")

    def set_collapse_delay_ms(self, delay_ms: int) -> None:
        """Set auto-collapse inactivity delay in milliseconds (clamped to 500-30000 ms)."""
        try:
            val = int(delay_ms)
        except (ValueError, TypeError):
            val = 3500
        val = max(500, min(30000, val))
        self.set("dynamic_island/collapse_delay_ms", val)


    def get_hotkey_show_hide(self) -> str:
        """Return global hotkey sequence string for Show/Hide window."""
        return str(self.get("hotkeys/show_hide"))

    def set_hotkey_show_hide(self, sequence: str) -> None:
        """Set global hotkey sequence string for Show/Hide window."""
        self.set("hotkeys/show_hide", str(sequence))

    def get_hotkey_play_pause(self) -> str:
        """Return global hotkey sequence string for Toggle Play/Pause."""
        return str(self.get("hotkeys/play_pause"))

    def set_hotkey_play_pause(self, sequence: str) -> None:
        """Set global hotkey sequence string for Toggle Play/Pause."""
        self.set("hotkeys/play_pause", str(sequence))

    # --- Audio & Equalizer Accessors ---

    def get_preamp_boost_db(self) -> float:
        """Return audio preamplifier volume boost in dB (0.0 to 12.0 dB)."""
        return float(self.get("audio/preamp_boost_db"))

    def set_preamp_boost_db(self, val: float) -> None:
        """Set audio preamplifier volume boost in dB (clamped 0.0 to 12.0 dB)."""
        clamped = max(0.0, min(12.0, float(val)))
        self.set("audio/preamp_boost_db", clamped)

    def get_bass_db(self) -> float:
        """Return bass boost/cut in dB (-12.0 to +12.0 dB)."""
        return float(self.get("audio/bass_db"))

    def set_bass_db(self, val: float) -> None:
        """Set bass boost/cut in dB (-12.0 to +12.0 dB)."""
        clamped = max(-12.0, min(12.0, float(val)))
        self.set("audio/bass_db", clamped)

    def get_clarity_db(self) -> float:
        """Return vocal/mid clarity filter in dB (-12.0 to +12.0 dB)."""
        return float(self.get("audio/clarity_db"))

    def set_clarity_db(self, val: float) -> None:
        """Set vocal/mid clarity filter in dB (-12.0 to +12.0 dB)."""
        clamped = max(-12.0, min(12.0, float(val)))
        self.set("audio/clarity_db", clamped)

    def get_treble_db(self) -> float:
        """Return treble/air filter in dB (-12.0 to +12.0 dB)."""
        return float(self.get("audio/treble_db"))

    def set_treble_db(self, val: float) -> None:
        """Set treble/air filter in dB (-12.0 to +12.0 dB)."""
        clamped = max(-12.0, min(12.0, float(val)))
        self.set("audio/treble_db", clamped)

    def get_noise_gate_percent(self) -> int:
        """Return noise gate/filter threshold percentage (0 to 50%)."""
        return int(self.get("audio/noise_gate_percent"))

    def set_noise_gate_percent(self, val: int) -> None:
        """Set noise gate/filter threshold percentage (0 to 50%)."""
        clamped = max(0, min(50, int(val)))
        self.set("audio/noise_gate_percent", clamped)

    def get_eq_preset(self) -> str:
        """Return current equalizer preset name."""
        return str(self.get("audio/eq_preset"))

    def set_eq_preset(self, preset: str) -> None:
        """Set current equalizer preset name."""
        self.set("audio/eq_preset", str(preset))

    def get_eq_bands(self) -> list:
        """Return 5-band graphic EQ values [60Hz, 250Hz, 1kHz, 4kHz, 16kHz] in dB."""
        keys = [
            "audio/eq_band_60",
            "audio/eq_band_250",
            "audio/eq_band_1000",
            "audio/eq_band_4000",
            "audio/eq_band_16000",
        ]
        return [float(self.get(k)) for k in keys]

    def set_eq_bands(self, bands: list) -> None:
        """Set 5-band graphic EQ values in dB (-12.0 to +12.0 dB)."""
        keys = [
            "audio/eq_band_60",
            "audio/eq_band_250",
            "audio/eq_band_1000",
            "audio/eq_band_4000",
            "audio/eq_band_16000",
        ]
        for i, k in enumerate(keys):
            v = bands[i] if i < len(bands) else 0.0
            clamped = max(-12.0, min(12.0, float(v)))
            self.set(k, clamped)

    def get_eq_enabled(self) -> bool:
        """Return whether equalizer and audio enhancement processing is enabled."""
        return bool(self.get("audio/eq_enabled"))

    def set_eq_enabled(self, enabled: bool) -> None:
        """Set whether equalizer and audio enhancement processing is enabled."""
        self.set("audio/eq_enabled", bool(enabled))

    def get_expand_trigger(self) -> str:
        """Return expansion trigger mode: 'hover' or 'click'."""
        val = str(self.get("dynamic_island/expand_trigger") or "hover").lower()
        return "click" if val == "click" else "hover"

    def set_expand_trigger(self, trigger: str) -> None:
        """Set expansion trigger mode: 'hover' or 'click'."""
        mode = "click" if str(trigger).lower() == "click" else "hover"
        self.set("dynamic_island/expand_trigger", mode)

    def get_hover_intent_delay_ms(self) -> int:
        """Return hover intent delay before expansion in milliseconds (default 150ms)."""
        return _to_int(self.get("dynamic_island/hover_intent_delay_ms"), 150)

    def set_hover_intent_delay_ms(self, delay_ms: int) -> None:
        """Set hover intent delay before expansion in milliseconds."""
        self.set("dynamic_island/hover_intent_delay_ms", max(0, min(1000, int(delay_ms))))

    def get_fullscreen_auto_hide(self) -> bool:
        """Return True if MediaDock automatically hides when a fullscreen game/app is active."""
        return bool(self.get("window/fullscreen_auto_hide"))

    def set_fullscreen_auto_hide(self, enabled: bool) -> None:
        """Set whether MediaDock automatically hides when a fullscreen game/app is active."""
        self.set("window/fullscreen_auto_hide", bool(enabled))

    def get_display_monitor(self) -> str:
        """Return selected monitor string ('primary', 'monitor_1', etc.)."""
        return str(self.get("window/display_monitor") or "primary")

    def set_display_monitor(self, monitor: str) -> None:
        """Set selected display monitor."""
        self.set("window/display_monitor", str(monitor))

    def get_spectrum_mode(self) -> str:
        """Return audio spectrum analysis mode: 'fft' or 'rms'."""
        val = str(self.get("audio/spectrum_mode") or "fft").lower()
        return "rms" if val == "rms" else "fft"

    def set_spectrum_mode(self, mode: str) -> None:
        """Set audio spectrum analysis mode: 'fft' or 'rms'."""
        val = "rms" if str(mode).lower() == "rms" else "fft"
        self.set("audio/spectrum_mode", val)

    def get_lyrics_enabled(self) -> bool:
        """Return True if synchronized lyrics display is enabled."""
        return bool(self.get("features/lyrics_enabled"))

    def set_lyrics_enabled(self, enabled: bool) -> None:
        """Set whether synchronized lyrics display is enabled."""
        self.set("features/lyrics_enabled", bool(enabled))

    def sync(self) -> None:
        """Synchronize in-memory settings to persistent QSettings storage."""
        self._settings.sync()

    def clear(self) -> None:
        """Reset all stored settings in the QSettings store."""
        self._settings.clear()
        self.sync()
