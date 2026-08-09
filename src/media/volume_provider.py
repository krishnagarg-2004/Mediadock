"""Volume provider interface and Windows CoreAudio implementation."""

import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional, Callable

from src.core.models import VolumeState

logger = logging.getLogger(__name__)

VolumeCallback = Callable[[VolumeState], None]


class BaseVolumeProvider(ABC):
    """Abstract interface defining the contract for system volume controls."""

    @abstractmethod
    def get_volume_state(self) -> VolumeState:
        """Return current VolumeState or VolumeState.unsupported()."""
        pass

    @abstractmethod
    def set_volume(self, percent: int) -> bool:
        """Set master volume percentage (0 to 100). Returns True if successful."""
        pass

    @abstractmethod
    def set_mute(self, muted: bool) -> bool:
        """Set mute state. Returns True if successful."""
        pass

    @abstractmethod
    def toggle_mute(self) -> bool:
        """Toggle mute state. Returns True if successful."""
        pass

    @abstractmethod
    def set_on_volume_changed(self, callback: Optional[VolumeCallback]) -> None:
        """Register callback for volume state change notifications."""
        pass

    def start_listening(self) -> None:
        """Initialize provider connections and listeners."""
        pass

    def stop_listening(self) -> None:
        """Unregister event listeners and clean up resources."""
        pass


class WindowsVolumeProvider(BaseVolumeProvider):
    """Windows master audio volume provider using Windows CoreAudio COM APIs."""

    def __init__(
        self,
        on_volume_changed: Optional[VolumeCallback] = None,
    ) -> None:
        self._on_volume_changed_cb = on_volume_changed
        self._lock = threading.RLock()
        self._is_supported = False
        self._endpoint_volume = None
        self._initialized = False

        self._init_core_audio()

    def _init_core_audio(self) -> None:
        """Initialize Windows CoreAudio IAudioEndpointVolume COM interface safely."""
        try:
            import ctypes
            from ctypes import HRESULT, POINTER, Structure, c_float, byref, c_int, c_void_p, WINFUNCTYPE, cast
            from ctypes.wintypes import DWORD, BOOL, LPCWSTR

            ole32 = ctypes.windll.ole32
            ole32.CoInitialize(None)

            class GUID(Structure):
                _fields_ = [
                    ("Data1", DWORD),
                    ("Data2", ctypes.c_ushort),
                    ("Data3", ctypes.c_ushort),
                    ("Data4", ctypes.c_ubyte * 8),
                ]

            def clsid_from_string(s: str) -> GUID:
                guid = GUID()
                ole32.CLSIDFromString(LPCWSTR(s), byref(guid))
                return guid

            CLSID_MMDeviceEnumerator = clsid_from_string("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
            IID_IMMDeviceEnumerator = clsid_from_string("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
            IID_IAudioEndpointVolume = clsid_from_string("{5CD8FA44-4F33-4615-A2FE-5C4293D48B27}")

            device_enum = c_void_p()
            hr = ole32.CoCreateInstance(
                byref(CLSID_MMDeviceEnumerator),
                None,
                1,  # CLSCTX_INPROC_SERVER
                byref(IID_IMMDeviceEnumerator),
                byref(device_enum),
            )
            if hr != 0 or not device_enum:
                logger.warning("Failed to create MMDeviceEnumerator COM object: %s", hex(hr & 0xFFFFFFFF))
                return

            vtbl_enum = cast(device_enum, POINTER(POINTER(c_void_p))).contents
            get_default_endpoint = WINFUNCTYPE(HRESULT, c_void_p, c_int, c_int, POINTER(c_void_p))(vtbl_enum[4])

            device = c_void_p()
            hr = get_default_endpoint(device_enum, 0, 0, byref(device))  # eRender=0, eConsole=0
            if hr != 0 or not device:
                logger.warning("Failed to get default audio endpoint: %s", hex(hr & 0xFFFFFFFF))
                return

            vtbl_dev = cast(device, POINTER(POINTER(c_void_p))).contents
            activate = WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), DWORD, c_void_p, POINTER(c_void_p))(vtbl_dev[3])

            audio_vol = c_void_p()
            hr = activate(device, byref(IID_IAudioEndpointVolume), 1, None, byref(audio_vol))
            if hr != 0 or not audio_vol:
                logger.warning("IAudioEndpointVolume interface not supported on default endpoint: %s", hex(hr & 0xFFFFFFFF))
                return

            self._endpoint_volume = audio_vol
            self._is_supported = True
            self._initialized = True
        except Exception as e:
            logger.warning("Windows CoreAudio initialization unavailable: %s", e)
            self._is_supported = False
            self._endpoint_volume = None

    def get_volume_state(self) -> VolumeState:
        """Query system master volume and mute state."""
        with self._lock:
            if not self._is_supported or not self._endpoint_volume:
                return VolumeState.unsupported()

        try:
            import ctypes
            from ctypes import HRESULT, POINTER, byref, c_float, c_void_p, WINFUNCTYPE, cast
            from ctypes.wintypes import BOOL

            vtbl_vol = cast(self._endpoint_volume, POINTER(POINTER(c_void_p))).contents

            # GetMasterVolumeLevelScalar (vtable index 9)
            get_vol = WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))(vtbl_vol[9])
            vol_scalar = c_float()
            hr_vol = get_vol(self._endpoint_volume, byref(vol_scalar))

            # GetMute (vtable index 14)
            get_mute = WINFUNCTYPE(HRESULT, c_void_p, POINTER(BOOL))(vtbl_vol[14])
            muted = BOOL()
            hr_mute = get_mute(self._endpoint_volume, byref(muted))

            if hr_vol == 0 and hr_mute == 0:
                percent = max(0, min(100, int(round(vol_scalar.value * 100.0))))
                return VolumeState(volume_percent=percent, is_muted=bool(muted.value), is_supported=True)
        except Exception as e:
            logger.warning("Error reading Windows volume state: %s", e)

        return VolumeState.unsupported()

    def set_volume(self, percent: int) -> bool:
        """Set master volume percentage (clamped to 0–100%)."""
        clamped = max(0, min(100, percent))
        with self._lock:
            if not self._is_supported or not self._endpoint_volume:
                return False

        try:
            import ctypes
            from ctypes import HRESULT, POINTER, byref, c_float, c_void_p, WINFUNCTYPE, cast

            vtbl_vol = cast(self._endpoint_volume, POINTER(POINTER(c_void_p))).contents

            # SetMasterVolumeLevelScalar (vtable index 7)
            set_vol = WINFUNCTYPE(HRESULT, c_void_p, c_float, c_void_p)(vtbl_vol[7])
            scalar = c_float(clamped / 100.0)
            hr = set_vol(self._endpoint_volume, scalar, None)
            if hr == 0:
                self._notify_volume_changed()
                return True
        except Exception as e:
            logger.warning("Error setting Windows master volume: %s", e)

        return False

    def set_mute(self, muted: bool) -> bool:
        """Set master mute state."""
        with self._lock:
            if not self._is_supported or not self._endpoint_volume:
                return False

        try:
            import ctypes
            from ctypes import HRESULT, POINTER, c_void_p, WINFUNCTYPE, cast
            from ctypes.wintypes import BOOL

            vtbl_vol = cast(self._endpoint_volume, POINTER(POINTER(c_void_p))).contents

            # SetMute (vtable index 13)
            set_mute_func = WINFUNCTYPE(HRESULT, c_void_p, BOOL, c_void_p)(vtbl_vol[13])
            hr = set_mute_func(self._endpoint_volume, BOOL(muted), None)
            if hr == 0:
                self._notify_volume_changed()
                return True
        except Exception as e:
            logger.warning("Error setting Windows mute state: %s", e)

        return False

    def toggle_mute(self) -> bool:
        """Toggle current mute state."""
        current_state = self.get_volume_state()
        if not current_state.is_supported:
            return False
        return self.set_mute(not current_state.is_muted)

    def set_on_volume_changed(self, callback: Optional[VolumeCallback]) -> None:
        """Register callback handler for volume state changes."""
        with self._lock:
            self._on_volume_changed_cb = callback

    def _notify_volume_changed(self) -> None:
        """Invoke volume change callback with current VolumeState."""
        with self._lock:
            cb = self._on_volume_changed_cb

        if cb:
            state = self.get_volume_state()
            try:
                cb(state)
            except Exception as e:
                logger.error("Error in volume change callback: %s", e)
