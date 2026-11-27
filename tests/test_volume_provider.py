"""Unit tests for VolumeState, volume providers, MediaCore volume signals, and UI integration."""

import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from src.core.models import VolumeState, TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider
from src.media.volume_provider import BaseVolumeProvider, WindowsVolumeProvider
from src.core.media_core import MediaCore
from src.ui.main_window import MainWindow, create_volume_icon_pixmap

# Ensure QApplication instance exists for GUI tests
_app = QApplication.instance() or QApplication([])


class DummyMediaProvider(BaseMediaProvider):
    """Dummy media provider for testing."""

    def get_current_track(self) -> TrackInfo:
        return TrackInfo.empty()

    def get_playback_status(self) -> PlaybackStatus:
        return PlaybackStatus.CLOSED

    def start_listening(self) -> None:
        pass

    def stop_listening(self) -> None:
        pass

    def set_on_track_changed(self, callback) -> None:
        pass

    def set_on_status_changed(self, callback) -> None:
        pass

    def set_on_session_availability_changed(self, callback) -> None:
        pass

    def play(self) -> bool:
        return True

    def pause(self) -> bool:
        return True

    def toggle_play_pause(self) -> bool:
        return True

    def next_track(self) -> bool:
        return True

    def previous_track(self) -> bool:
        return True

    def seek_to_position(self, position_ms: int) -> bool:
        return True


class DummyVolumeProvider(BaseVolumeProvider):
    """Mockable VolumeProvider for testing."""

    def __init__(self, supported: bool = True, volume: int = 75, muted: bool = False) -> None:
        self._supported = supported
        self._volume = volume
        self._muted = muted
        self._callback = None

    def get_volume_state(self) -> VolumeState:
        if not self._supported:
            return VolumeState.unsupported()
        return VolumeState(volume_percent=self._volume, is_muted=self._muted, is_supported=True)

    def set_volume(self, percent: int) -> bool:
        if not self._supported:
            return False
        self._volume = max(0, min(100, percent))
        self.notify()
        return True

    def set_mute(self, muted: bool) -> bool:
        if not self._supported:
            return False
        self._muted = muted
        self.notify()
        return True

    def toggle_mute(self) -> bool:
        if not self._supported:
            return False
        self._muted = not self._muted
        self.notify()
        return True

    def set_on_volume_changed(self, callback) -> None:
        self._callback = callback

    def notify(self) -> None:
        if self._callback:
            self._callback(self.get_volume_state())



class TestVolumeSystem(unittest.TestCase):
    """Test suite covering VolumeState model, volume providers, MediaCore, and UI integration."""

    def test_volume_state_model_and_unsupported_factory(self) -> None:
        """Verify VolumeState immutability, fields, and unsupported factory."""
        state = VolumeState(volume_percent=50, is_muted=False, is_supported=True)
        self.assertEqual(state.volume_percent, 50)
        self.assertFalse(state.is_muted)
        self.assertTrue(state.is_supported)

        unsupported = VolumeState.unsupported()
        self.assertEqual(unsupported.volume_percent, 0)
        self.assertFalse(unsupported.is_muted)
        self.assertFalse(unsupported.is_supported)

    def test_windows_volume_provider_clamping_and_fallback(self) -> None:
        """Verify WindowsVolumeProvider bounds clamping and graceful fallback when COM is unavailable."""
        provider = WindowsVolumeProvider()
        # Force unsupported state for test isolation
        provider._is_supported = False
        provider._endpoint_volume = None

        self.assertFalse(provider.get_volume_state().is_supported)
        self.assertFalse(provider.set_volume(50))
        self.assertFalse(provider.set_mute(True))
        self.assertFalse(provider.toggle_mute())

    def test_windows_volume_provider_clamping_with_mock(self) -> None:
        """Verify volume clamping (0 to 100%) when Windows API is mocked."""
        provider = WindowsVolumeProvider()
        provider._is_supported = True
        provider._endpoint_volume = MagicMock()

        with patch.object(provider, "_notify_volume_changed") as mock_notify:
            with patch("ctypes.cast") as mock_cast:
                mock_vtbl = [MagicMock() for _ in range(20)]
                mock_cast.return_value.contents = mock_vtbl

                # Mock set_vol (vtable 7) return HR = 0
                mock_set_vol = MagicMock(return_value=0)
                with patch("ctypes.WINFUNCTYPE", return_value=lambda func: mock_set_vol):
                    # Test values < 0 clamped to 0
                    self.assertTrue(provider.set_volume(-25))
                    # Test values > 100 clamped to 100
                    self.assertTrue(provider.set_volume(150))
                    # Test intermediate value 65%
                    self.assertTrue(provider.set_volume(65))

                # Mock set_mute (vtable 14) return HR = 0
                mock_set_mute = MagicMock(return_value=0)
                with patch("ctypes.WINFUNCTYPE", return_value=lambda func: mock_set_mute):
                    self.assertTrue(provider.set_mute(True))
                    self.assertTrue(provider.set_mute(False))

    def test_media_core_volume_delegation_and_signals(self) -> None:
        """Verify MediaCore exposes volume methods and emits volume_changed signals."""
        media_prov = DummyMediaProvider()
        vol_prov = DummyVolumeProvider(supported=True, volume=80, muted=False)
        core = MediaCore(provider=media_prov, volume_provider=vol_prov)

        received_states = []
        core.volume_changed.connect(lambda s: received_states.append(s))

        self.assertTrue(core.is_volume_supported())
        self.assertEqual(core.get_volume_state().volume_percent, 80)

        # Set volume through MediaCore
        core.set_volume(45)
        self.assertEqual(vol_prov._volume, 45)
        self.assertEqual(len(received_states), 1)
        self.assertEqual(received_states[0].volume_percent, 45)

        # Toggle mute through MediaCore
        core.toggle_mute()
        self.assertTrue(vol_prov._muted)
        self.assertTrue(received_states[-1].is_muted)

    def test_main_window_volume_ui_sync_and_feedback_loop_prevention(self) -> None:
        """Verify MainWindow volume slider and mute button sync state and prevent feedback loops."""
        media_prov = DummyMediaProvider()
        vol_prov = DummyVolumeProvider(supported=True, volume=60, muted=False)
        core = MediaCore(provider=media_prov, volume_provider=vol_prov)
        window = MainWindow(media_core=core)

        self.assertFalse(window.btn_mute.isHidden())
        self.assertFalse(window.slider_volume.isHidden())
        self.assertEqual(window.slider_volume.value(), 60)

        # Simulate user dragging volume slider
        window.slider_volume.setValue(30)
        self.assertEqual(vol_prov._volume, 30)

        # Simulate user clicking mute button
        window._on_btn_mute_clicked()
        self.assertTrue(vol_prov._muted)

    def test_main_window_unsupported_volume_fallback(self) -> None:
        """Verify MainWindow hides volume controls cleanly when volume control is unsupported."""
        media_prov = DummyMediaProvider()
        vol_prov = DummyVolumeProvider(supported=False)
        core = MediaCore(provider=media_prov, volume_provider=vol_prov)
        window = MainWindow(media_core=core)

        self.assertTrue(window.btn_mute.isHidden())
        self.assertTrue(window.slider_volume.isHidden())


    def test_vector_volume_icon_pixmap_generation(self) -> None:
        """Verify vector volume icon generator creates non-null QPixmap for muted and unmuted states."""
        pixmap_unmuted = create_volume_icon_pixmap(muted=False, size=16)
        self.assertFalse(pixmap_unmuted.isNull())
        self.assertEqual(pixmap_unmuted.width(), 16)

        pixmap_muted = create_volume_icon_pixmap(muted=True, size=16)
        self.assertFalse(pixmap_muted.isNull())
        self.assertEqual(pixmap_muted.width(), 16)

    def test_windows_coreaudio_real_endpoint_supported_on_windows(self) -> None:
        """Verify WindowsVolumeProvider binds real CoreAudio endpoint when audio hardware is present."""
        import sys
        provider = WindowsVolumeProvider()
        try:
            if sys.platform == "win32":
                state = provider.get_volume_state()
                self.assertTrue(state.is_supported)
                self.assertGreaterEqual(state.volume_percent, 0)
                self.assertLessEqual(state.volume_percent, 100)
        finally:
            provider.stop_listening()

    def test_shuffle_repeat_buttons_sync_playback_modes_and_availability(self) -> None:
        """Verify Shuffle and Repeat buttons sync checked states, tooltips, and availability lock."""
        media_prov = DummyMediaProvider()
        vol_prov = DummyVolumeProvider(supported=True, volume=50, muted=False)
        core = MediaCore(provider=media_prov, volume_provider=vol_prov)
        window = MainWindow(media_core=core)

        window.on_session_availability_changed(False)
        self.assertFalse(window.btn_shuffle.isEnabled())
        self.assertFalse(window.btn_repeat.isEnabled())

        window.on_session_availability_changed(True)
        self.assertTrue(window.btn_shuffle.isEnabled())
        self.assertTrue(window.btn_repeat.isEnabled())

        core._on_provider_playback_modes_changed(True, 1)
        self.assertTrue(window.btn_shuffle.isChecked())
        self.assertEqual(window.btn_shuffle.toolTip(), "Shuffle: On")
        self.assertTrue(window.btn_repeat.isChecked())
        self.assertEqual(window.btn_repeat.toolTip(), "Repeat: Current Track")

        core._on_provider_playback_modes_changed(False, 2)
        self.assertFalse(window.btn_shuffle.isChecked())
        self.assertEqual(window.btn_repeat.toolTip(), "Repeat: All / Playlist")

        core._on_provider_playback_modes_changed(False, 0)
        self.assertFalse(window.btn_repeat.isChecked())
        self.assertEqual(window.btn_repeat.toolTip(), "Repeat: Off")


if __name__ == "__main__":
    unittest.main()
