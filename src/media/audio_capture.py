"""Windows WASAPI loopback audio capture layer for real-time media visualization.

Provides native Windows loopback capture from default render endpoint without requiring
a microphone, using standard library ctypes COM bindings.
"""

from dataclasses import dataclass
from typing import Sequence, Optional, Callable
from abc import ABC, abstractmethod
import logging
import threading
import time
import sys

logger = logging.getLogger(__name__)


@dataclass
class AudioFrame:
    """Container holding raw PCM audio sample data and format metadata."""

    samples: Sequence[float]
    sample_rate: int
    channels: int
    frame_count: int


AudioCallback = Callable[[AudioFrame], None]


class BaseAudioCapture(ABC):
    """Abstract interface defining contract for audio capture implementations."""

    @abstractmethod
    def start(self) -> bool:
        """Start continuous audio capture. Return True if successful."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop audio capture and release resources."""
        pass

    @abstractmethod
    def is_capturing(self) -> bool:
        """Return True if capture is currently active."""
        pass

    @abstractmethod
    def set_on_audio_frame(self, callback: Optional[AudioCallback]) -> None:
        """Register callback for captured audio frame notifications."""
        pass


# Windows HRESULT Constants
S_OK = 0
AUDCLNT_E_DEVICE_INVALIDATED = 0x88890004
AUDCLNT_E_RESOURCES_INVALIDATED = 0x88890026
AUDCLNT_E_SERVICE_NOT_RUNNING = 0x88890006


class WASAPILoopbackCapture(BaseAudioCapture):
    """Windows system render loopback audio capture using native ctypes COM APIs."""

    def __init__(
        self,
        on_audio_frame: Optional[AudioCallback] = None,
        target_buffer_duration_ms: int = 100,
    ) -> None:
        self._on_audio_frame_cb = on_audio_frame
        self._buffer_duration_hnsec = target_buffer_duration_ms * 10000  # 100ns units
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_capturing = False
        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        """Return description of the last encountered error, if any."""
        with self._lock:
            return self._last_error

    def set_on_audio_frame(self, callback: Optional[AudioCallback]) -> None:
        """Register or update audio frame callback."""
        with self._lock:
            self._on_audio_frame_cb = callback

    def is_capturing(self) -> bool:
        """Check if audio capture thread is currently running."""
        with self._lock:
            return self._is_capturing and self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """Start background worker thread for WASAPI loopback capture."""
        with self._lock:
            if self.is_capturing():
                return True

            self._stop_event.clear()
            self._last_error = None
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="WASAPILoopbackThread",
                daemon=True,
            )
            self._thread.start()

        # Brief wait to verify thread startup status
        time.sleep(0.05)
        return self.is_capturing()

    def stop(self) -> None:
        """Signal capture thread to stop and wait for clean termination."""
        with self._lock:
            self._stop_event.set()
            thread = self._thread
            self._thread = None

        if thread and thread.is_alive():
            thread.join(timeout=2.0)

        with self._lock:
            self._is_capturing = False

    def _worker_loop(self) -> None:
        """Worker thread entry point handling COM lifecycle and continuous capture."""
        if sys.platform != "win32":
            with self._lock:
                self._last_error = "WASAPI loopback is only available on Windows platforms."
                self._is_capturing = False
            return

        try:
            import ctypes
            ole32 = ctypes.windll.ole32
            ole32.CoInitialize(None)
        except Exception as e:
            logger.warning("COM CoInitialize failed in WASAPI worker thread: %s", e)
            with self._lock:
                self._last_error = f"COM initialization failed: {e}"
                self._is_capturing = False
            return

        try:
            with self._lock:
                self._is_capturing = True

            while not self._stop_event.is_set():
                session_ok = self._run_capture_session()
                if self._stop_event.is_set():
                    break

                if not session_ok:
                    # Device invalidation or init error — pause briefly before retry
                    time.sleep(0.5)

        except Exception as e:
            logger.warning("Unhandled exception in WASAPI capture worker: %s", e)
            with self._lock:
                self._last_error = str(e)
        finally:
            with self._lock:
                self._is_capturing = False
            try:
                ole32.CoUninitialize()
            except Exception:
                pass

    def _run_capture_session(self) -> bool:
        """Initialize CoreAudio objects and drain packets until stopped or invalidated."""
        import ctypes
        from ctypes import HRESULT, POINTER, Structure, c_float, byref, c_int, c_int64, c_uint32, c_void_p, WINFUNCTYPE, cast
        from ctypes.wintypes import DWORD, WORD, BYTE, LPCWSTR

        ole32 = ctypes.windll.ole32

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
        IID_IAudioClient = clsid_from_string("{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}")
        IID_IAudioCaptureClient = clsid_from_string("{C8ADBD64-E71E-48a0-A4DE-185C395CD317}")

        class WAVEFORMATEX(Structure):
            _fields_ = [
                ("wFormatTag", WORD),
                ("nChannels", WORD),
                ("nSamplesPerSec", DWORD),
                ("nAvgBytesPerSec", DWORD),
                ("nBlockAlign", WORD),
                ("wBitsPerSample", WORD),
                ("cbSize", WORD),
            ]

        capture_client = c_void_p()
        audio_client = c_void_p()
        device = c_void_p()
        device_enum = c_void_p()
        pwfx = POINTER(WAVEFORMATEX)()

        def _release_ptr(ptr) -> None:
            if not ptr:
                return
            try:
                from ctypes import c_ulong
                vtbl = cast(ptr, POINTER(POINTER(c_void_p))).contents
                WINFUNCTYPE(c_ulong, c_void_p)(vtbl[2])(ptr)
            except Exception:
                pass

        try:
            hr = ole32.CoCreateInstance(
                byref(CLSID_MMDeviceEnumerator),
                None,
                1,  # CLSCTX_INPROC_SERVER
                byref(IID_IMMDeviceEnumerator),
                byref(device_enum),
            )
            if hr != 0 or not device_enum:
                logger.warning("WASAPI: Failed to CoCreate MMDeviceEnumerator: %s", hex(hr & 0xFFFFFFFF))
                return False

            vtbl_enum = cast(device_enum, POINTER(POINTER(c_void_p))).contents
            get_default_endpoint = WINFUNCTYPE(HRESULT, c_void_p, c_int, c_int, POINTER(c_void_p))(vtbl_enum[4])

            hr = get_default_endpoint(device_enum, 0, 0, byref(device))  # eRender=0, eConsole=0
            if hr != 0 or not device:
                logger.warning("WASAPI: Failed to get default audio endpoint: %s", hex(hr & 0xFFFFFFFF))
                return False

            vtbl_dev = cast(device, POINTER(POINTER(c_void_p))).contents
            activate = WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), DWORD, c_void_p, POINTER(c_void_p))(vtbl_dev[3])

            hr = activate(device, byref(IID_IAudioClient), 1, None, byref(audio_client))
            if hr != 0 or not audio_client:
                logger.warning("WASAPI: Failed to activate IAudioClient interface: %s", hex(hr & 0xFFFFFFFF))
                return False

            vtbl_client = cast(audio_client, POINTER(POINTER(c_void_p))).contents

            get_mix_format = WINFUNCTYPE(HRESULT, c_void_p, POINTER(POINTER(WAVEFORMATEX)))(vtbl_client[8])
            hr = get_mix_format(audio_client, byref(pwfx))
            if hr != 0 or not pwfx:
                logger.warning("WASAPI: Failed to get audio mix format: %s", hex(hr & 0xFFFFFFFF))
                return False

            wfx = pwfx.contents
            sample_rate = int(wfx.nSamplesPerSec)
            channels = int(wfx.nChannels)

            AUDCLNT_SHAREMODE_SHARED = 0
            AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000

            init_client = WINFUNCTYPE(
                HRESULT, c_void_p, c_int, DWORD, c_int64, c_int64, POINTER(WAVEFORMATEX), c_void_p
            )(vtbl_client[3])
            hr = init_client(
                audio_client,
                AUDCLNT_SHAREMODE_SHARED,
                AUDCLNT_STREAMFLAGS_LOOPBACK,
                self._buffer_duration_hnsec,
                0,
                pwfx,
                None,
            )
            if hr != 0:
                logger.warning("WASAPI: Failed to initialize IAudioClient in loopback mode: %s", hex(hr & 0xFFFFFFFF))
                return False

            get_service = WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), POINTER(c_void_p))(vtbl_client[14])
            hr = get_service(audio_client, byref(IID_IAudioCaptureClient), byref(capture_client))
            if hr != 0 or not capture_client:
                logger.warning("WASAPI: Failed to get IAudioCaptureClient service: %s", hex(hr & 0xFFFFFFFF))
                return False

            vtbl_cap = cast(capture_client, POINTER(POINTER(c_void_p))).contents
            start_client = WINFUNCTYPE(HRESULT, c_void_p)(vtbl_client[10])
            stop_client = WINFUNCTYPE(HRESULT, c_void_p)(vtbl_client[11])
            get_buffer = WINFUNCTYPE(
                HRESULT,
                c_void_p,
                POINTER(POINTER(BYTE)),
                POINTER(c_uint32),
                POINTER(DWORD),
                POINTER(c_int64),
                POINTER(c_int64),
            )(vtbl_cap[3])
            release_buffer = WINFUNCTYPE(HRESULT, c_void_p, c_uint32)(vtbl_cap[4])
            get_next_packet_size = WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_uint32))(vtbl_cap[5])

            hr = start_client(audio_client)
            if hr != 0:
                logger.warning("WASAPI: Failed to start IAudioClient: %s", hex(hr & 0xFFFFFFFF))
                return False

            p_data = POINTER(BYTE)()
            num_frames = c_uint32()
            flags = DWORD()
            device_pos = c_int64()
            qpc_pos = c_int64()
            packet_size = c_uint32()

            try:
                while not self._stop_event.is_set():
                    hr = get_next_packet_size(capture_client, byref(packet_size))
                    if hr != 0:
                        code = hr & 0xFFFFFFFF
                        if code in (AUDCLNT_E_DEVICE_INVALIDATED, AUDCLNT_E_RESOURCES_INVALIDATED, AUDCLNT_E_SERVICE_NOT_RUNNING):
                            logger.warning("WASAPI: Audio device invalidated or service stopped: %s", hex(code))
                            return False
                        time.sleep(0.01)
                        continue

                    packets_drained = 0
                    while packet_size.value > 0 and not self._stop_event.is_set():
                        hr = get_buffer(
                            capture_client,
                            byref(p_data),
                            byref(num_frames),
                            byref(flags),
                            byref(device_pos),
                            byref(qpc_pos),
                        )
                        if hr != 0:
                            code = hr & 0xFFFFFFFF
                            if code in (AUDCLNT_E_DEVICE_INVALIDATED, AUDCLNT_E_RESOURCES_INVALIDATED, AUDCLNT_E_SERVICE_NOT_RUNNING):
                                logger.warning("WASAPI: Audio device invalidated during GetBuffer: %s", hex(code))
                                return False
                            break

                        frames = num_frames.value
                        if frames > 0 and p_data:
                            sample_count = frames * channels
                            float_ptr = cast(p_data, POINTER(c_float))
                            samples = [float_ptr[i] for i in range(sample_count)]

                            frame = AudioFrame(
                                samples=samples,
                                sample_rate=sample_rate,
                                channels=channels,
                                frame_count=frames,
                            )
                            self._notify_audio_frame(frame)

                        release_buffer(capture_client, frames)
                        packets_drained += 1
                        get_next_packet_size(capture_client, byref(packet_size))

                    if packets_drained == 0:
                        time.sleep(0.01)

            finally:
                try:
                    stop_client(audio_client)
                except Exception:
                    pass

            return True
        finally:
            if pwfx:
                try:
                    ole32.CoTaskMemFree(pwfx)
                except Exception:
                    pass
            _release_ptr(capture_client)
            _release_ptr(audio_client)
            _release_ptr(device)
            _release_ptr(device_enum)

    def _notify_audio_frame(self, frame: AudioFrame) -> None:
        """Invoke registered audio frame callback safely."""
        with self._lock:
            cb = self._on_audio_frame_cb

        if cb:
            try:
                cb(frame)
            except Exception as e:
                logger.error("Error in audio frame callback: %s", e)
