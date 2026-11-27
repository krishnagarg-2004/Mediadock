"""Volume provider interface and Windows CoreAudio implementation."""

import logging
import sys
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional, Callable, Tuple

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

    def set_app_volume(self, app_name_or_id: str, percent: int) -> bool:
        """Set volume for a specific application session, falling back to master volume."""
        return self.set_volume(percent)

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
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_polled_state: Optional[Tuple[int, bool]] = None

        self._init_core_audio()

    @staticmethod
    def _release_com_ptr(ptr) -> None:
        """Safely invoke IUnknown::Release() on a raw COM c_void_p pointer."""
        if not ptr:
            return
        try:
            import ctypes
            from ctypes import POINTER, c_ulong, c_void_p, WINFUNCTYPE, cast
            vtbl = cast(ptr, POINTER(POINTER(c_void_p))).contents
            release_fn = WINFUNCTYPE(c_ulong, c_void_p)(vtbl[2])
            release_fn(ptr)
        except Exception:
            pass

    def _release_core_audio(self) -> None:
        """Release active COM endpoint pointer and mark CoreAudio uninitialized."""
        import ctypes
        with self._lock:
            ep = self._endpoint_volume
            self._endpoint_volume = None
            self._is_supported = False
            self._initialized = False
        if isinstance(ep, ctypes.c_void_p) and ep.value:
            self._release_com_ptr(ep)

    def _init_core_audio(self) -> None:
        """Initialize Windows CoreAudio IAudioEndpointVolume COM interface safely."""
        if sys.platform != "win32":
            self._is_supported = False
            self._endpoint_volume = None
            return

        device_enum = None
        device = None
        try:
            import ctypes
            from ctypes import HRESULT, POINTER, Structure, byref, c_int, c_void_p, WINFUNCTYPE, cast
            from ctypes.wintypes import DWORD, LPCWSTR

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
            # Microsoft documented IID for IAudioEndpointVolume
            IID_IAudioEndpointVolume = clsid_from_string("{5CDF2C82-841E-4546-9722-0CF74078229A}")

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

            with self._lock:
                self._release_core_audio()
                self._endpoint_volume = audio_vol
                self._is_supported = True
                self._initialized = True
        except Exception as e:
            logger.warning("Windows CoreAudio initialization unavailable: %s", e)
            with self._lock:
                self._is_supported = False
                self._endpoint_volume = None
        finally:
            self._release_com_ptr(device)
            self._release_com_ptr(device_enum)

    def start_listening(self) -> None:
        """Start lightweight background monitor syncing external Windows volume/mute changes."""
        if sys.platform != "win32":
            return
        with self._lock:
            if self._monitor_thread and self._monitor_thread.is_alive():
                return
            self._stop_event.clear()
            cur = self.get_volume_state()
            self._last_polled_state = (cur.volume_percent, cur.is_muted) if cur.is_supported else None
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="CoreAudioVolumeMonitor",
                daemon=True,
            )
            self._monitor_thread.start()

    def stop_listening(self) -> None:
        """Stop background volume monitor thread and release CoreAudio COM resources."""
        self._stop_event.set()
        with self._lock:
            thread = self._monitor_thread
            self._monitor_thread = None
        if thread and thread.is_alive():
            thread.join(timeout=1.5)
        self._release_core_audio()

    def _monitor_loop(self) -> None:
        """Poll Windows master volume/mute every 450ms and re-bind cleanly if playback device changes."""
        ole32 = None
        if sys.platform == "win32":
            try:
                import ctypes
                ole32 = ctypes.windll.ole32
                ole32.CoInitialize(None)
            except Exception:
                ole32 = None

        try:
            while not self._stop_event.is_set():
                state = self.get_volume_state()
                if not state.is_supported:
                    self._init_core_audio()
                    state = self.get_volume_state()
                    if state.is_supported:
                        sig = (state.volume_percent, state.is_muted)
                        self._last_polled_state = sig
                        self._notify_volume_changed()
                else:
                    sig = (state.volume_percent, state.is_muted)
                    if sig != self._last_polled_state:
                        self._last_polled_state = sig
                        self._notify_volume_changed()
                self._stop_event.wait(0.45)
        finally:
            if ole32 is not None:
                try:
                    ole32.CoUninitialize()
                except Exception:
                    pass

    def get_volume_state(self) -> VolumeState:
        """Query system master volume and mute state."""
        with self._lock:
            if not self._is_supported or not self._endpoint_volume:
                return VolumeState.unsupported()
            endpoint = self._endpoint_volume

        try:
            import ctypes
            from ctypes import HRESULT, POINTER, byref, c_float, c_void_p, WINFUNCTYPE, cast
            from ctypes.wintypes import BOOL

            vtbl_vol = cast(endpoint, POINTER(POINTER(c_void_p))).contents

            # GetMasterVolumeLevelScalar (vtable index 9)
            get_vol = WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))(vtbl_vol[9])
            vol_scalar = c_float()
            hr_vol = get_vol(endpoint, byref(vol_scalar))

            # GetMute (vtable index 14)
            get_mute = WINFUNCTYPE(HRESULT, c_void_p, POINTER(BOOL))(vtbl_vol[14])
            muted = BOOL()
            hr_mute = get_mute(endpoint, byref(muted))

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
            endpoint = self._endpoint_volume

        try:
            import ctypes
            from ctypes import HRESULT, POINTER, c_float, c_void_p, WINFUNCTYPE, cast

            vtbl_vol = cast(endpoint, POINTER(POINTER(c_void_p))).contents

            # SetMasterVolumeLevelScalar (vtable index 7)
            # Pass a zero-GUID as event context so Windows shows the OSD overlay animation.
            # Passing None suppresses the OSD; a valid GUID pointer re-enables it.
            import ctypes
            from ctypes import Structure, c_ulong, c_ushort, c_ubyte, byref as _byref

            class _GUID(Structure):
                _fields_ = [
                    ("Data1", c_ulong),
                    ("Data2", c_ushort),
                    ("Data3", c_ushort),
                    ("Data4", c_ubyte * 8),
                ]

            zero_guid = _GUID()
            set_vol = WINFUNCTYPE(HRESULT, c_void_p, c_float, c_void_p)(vtbl_vol[7])
            scalar = c_float(clamped / 100.0)
            hr = set_vol(endpoint, scalar, _byref(zero_guid))
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
            endpoint = self._endpoint_volume

        try:
            import ctypes
            from ctypes import HRESULT, POINTER, c_void_p, WINFUNCTYPE, cast
            from ctypes.wintypes import BOOL

            vtbl_vol = cast(endpoint, POINTER(POINTER(c_void_p))).contents

            # SetMute (vtable index 13)
            # Pass a zero-GUID as event context so Windows shows the OSD overlay animation.
            import ctypes
            from ctypes import Structure, c_ulong, c_ushort, c_ubyte, byref as _byref2

            class _GUID2(Structure):
                _fields_ = [
                    ("Data1", c_ulong),
                    ("Data2", c_ushort),
                    ("Data3", c_ushort),
                    ("Data4", c_ubyte * 8),
                ]

            zero_guid2 = _GUID2()
            set_mute_func = WINFUNCTYPE(HRESULT, c_void_p, BOOL, c_void_p)(vtbl_vol[13])
            hr = set_mute_func(endpoint, BOOL(muted), _byref2(zero_guid2))
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
