"""Unit tests for the BaseMediaProvider abstract class."""

import unittest
from src.core.models import TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider


class DummyMediaProvider(BaseMediaProvider):
    """Concrete implementation of BaseMediaProvider for testing."""

    def __init__(self) -> None:
        self.is_active = False
        self.track_cb = None
        self.status_cb = None
        self.session_cb = None

    def get_current_track(self) -> TrackInfo:
        return TrackInfo(title="Test Title", artist="Test Artist")

    def get_playback_status(self) -> PlaybackStatus:
        return PlaybackStatus.PLAYING

    def start_listening(self) -> None:
        self.is_active = True

    def stop_listening(self) -> None:
        self.is_active = False

    def set_on_track_changed(self, callback) -> None:
        self.track_cb = callback

    def set_on_status_changed(self, callback) -> None:
        self.status_cb = callback

    def set_on_session_availability_changed(self, callback) -> None:
        self.session_cb = callback

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


class TestBaseMediaProvider(unittest.TestCase):
    """Test suite for BaseMediaProvider abstraction."""

    def test_abstract_instantiation_raises_error(self) -> None:
        """Verify BaseMediaProvider cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            BaseMediaProvider()  # type: ignore[abstract]

    def test_concrete_subclass_instantiation(self) -> None:
        """Verify a concrete subclass implementing all methods can be instantiated."""
        provider = DummyMediaProvider()
        self.assertIsInstance(provider, BaseMediaProvider)
        self.assertFalse(provider.is_active)

    def test_provider_lifecycle(self) -> None:
        """Verify start_listening() and stop_listening() execute cleanly."""
        provider = DummyMediaProvider()
        provider.start_listening()
        self.assertTrue(provider.is_active)

        provider.stop_listening()
        self.assertFalse(provider.is_active)

    def test_get_current_track_returns_track_info(self) -> None:
        """Verify get_current_track() returns a TrackInfo instance."""
        provider = DummyMediaProvider()
        track = provider.get_current_track()
        self.assertIsInstance(track, TrackInfo)
        self.assertEqual(track.title, "Test Title")
        self.assertEqual(track.artist, "Test Artist")

    def test_get_playback_status_returns_playback_status(self) -> None:
        """Verify get_playback_status() returns a PlaybackStatus enum member."""
        provider = DummyMediaProvider()
        status = provider.get_playback_status()
        self.assertIsInstance(status, PlaybackStatus)
        self.assertEqual(status, PlaybackStatus.PLAYING)

    def test_transport_controls(self) -> None:
        """Verify concrete transport control methods return boolean values."""
        provider = DummyMediaProvider()
        self.assertTrue(provider.play())
        self.assertTrue(provider.pause())
        self.assertTrue(provider.toggle_play_pause())
        self.assertTrue(provider.next_track())
        self.assertTrue(provider.previous_track())
        self.assertTrue(provider.seek_to_position(1000))


if __name__ == "__main__":
    unittest.main()
