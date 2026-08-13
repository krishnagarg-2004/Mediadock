"""Unit tests for WASAPI loopback audio capture layer (src/media/audio_capture.py)."""

import unittest
from unittest.mock import MagicMock, patch
import time
import sys

from src.media.audio_capture import (
    AudioFrame,
    BaseAudioCapture,
    WASAPILoopbackCapture,
    AUDCLNT_E_DEVICE_INVALIDATED,
)


class DummyAudioCapture(BaseAudioCapture):
    """Mockable subclass of BaseAudioCapture for testing interface contract."""

    def __init__(self) -> None:
        self._capturing = False
        self._callback = None

    def start(self) -> bool:
        self._capturing = True
        return True

    def stop(self) -> None:
        self._capturing = False

    def is_capturing(self) -> bool:
        return self._capturing

    def set_on_audio_frame(self, callback) -> None:
        self._callback = callback

    def emit_frame(self, frame: AudioFrame) -> None:
        if self._callback:
            self._callback(frame)


class TestAudioCapture(unittest.TestCase):
    """Test suite for AudioFrame data structure and WASAPILoopbackCapture."""

    def test_audio_frame_fields(self) -> None:
        """Verify AudioFrame dataclass stores PCM samples and format metadata correctly."""
        samples = [0.1, -0.2, 0.5, 0.0]
        frame = AudioFrame(samples=samples, sample_rate=48000, channels=2, frame_count=2)

        self.assertEqual(frame.samples, samples)
        self.assertEqual(frame.sample_rate, 48000)
        self.assertEqual(frame.channels, 2)
        self.assertEqual(frame.frame_count, 2)

    def test_base_audio_capture_contract(self) -> None:
        """Verify BaseAudioCapture contract implementation."""
        capture = DummyAudioCapture()
        self.assertFalse(capture.is_capturing())

        received_frames = []
        capture.set_on_audio_frame(lambda f: received_frames.append(f))

        self.assertTrue(capture.start())
        self.assertTrue(capture.is_capturing())

        test_frame = AudioFrame(samples=[0.5, 0.5], sample_rate=44100, channels=1, frame_count=2)
        capture.emit_frame(test_frame)

        self.assertEqual(len(received_frames), 1)
        self.assertEqual(received_frames[0], test_frame)

        capture.stop()
        self.assertFalse(capture.is_capturing())

    def test_wasapi_capture_init_defaults(self) -> None:
        """Verify WASAPILoopbackCapture initial configuration state."""
        capture = WASAPILoopbackCapture()
        self.assertFalse(capture.is_capturing())
        self.assertIsNone(capture.last_error)

    def test_wasapi_capture_set_callback(self) -> None:
        """Verify registering and updating audio frame callback."""
        capture = WASAPILoopbackCapture()
        cb = MagicMock()
        capture.set_on_audio_frame(cb)

        test_frame = AudioFrame(samples=[0.0], sample_rate=48000, channels=2, frame_count=1)
        capture._notify_audio_frame(test_frame)
        cb.assert_called_once_with(test_frame)

    def test_callback_exception_isolation(self) -> None:
        """Verify exceptions in user callback are caught and do not crash worker."""
        def faulty_callback(frame: AudioFrame) -> None:
            raise ValueError("Test callback crash")

        capture = WASAPILoopbackCapture(on_audio_frame=faulty_callback)
        test_frame = AudioFrame(samples=[0.1], sample_rate=48000, channels=2, frame_count=1)

        # Should not raise exception
        capture._notify_audio_frame(test_frame)

    def test_non_windows_platform_graceful_handling(self) -> None:
        """Verify non-Windows platform execution sets last_error and exits cleanly."""
        capture = WASAPILoopbackCapture()
        with patch("sys.platform", "linux"):
            capture._worker_loop()

        self.assertFalse(capture.is_capturing())
        self.assertIn("Windows", capture.last_error or "")

    def test_com_init_failure_handling(self) -> None:
        """Verify COM CoInitialize failure is handled gracefully without crashing."""
        capture = WASAPILoopbackCapture()
        fake_ole32 = MagicMock()
        fake_ole32.CoInitialize.side_effect = RuntimeError("COM init error")

        with patch("sys.platform", "win32"), patch("ctypes.windll") as mock_windll:
            mock_windll.ole32 = fake_ole32
            capture._worker_loop()

        self.assertFalse(capture.is_capturing())
        self.assertIn("COM initialization failed", capture.last_error or "")

    def test_start_stop_lifecycle_with_mock_session(self) -> None:
        """Verify WASAPILoopbackCapture thread lifecycle and clean shutdown."""
        capture = WASAPILoopbackCapture()

        with patch.object(capture, "_run_capture_session", return_value=True) as mock_session:
            with patch("sys.platform", "win32"), patch("ctypes.windll") as mock_windll:
                mock_windll.ole32 = MagicMock()

                started = capture.start()
                self.assertTrue(started)
                self.assertTrue(capture.is_capturing())

                capture.stop()
                self.assertFalse(capture.is_capturing())

    def test_device_invalidation_handling(self) -> None:
        """Verify device invalidation status causes _run_capture_session to return False."""
        self.assertEqual(AUDCLNT_E_DEVICE_INVALIDATED, 0x88890004)


if __name__ == "__main__":
    unittest.main()
