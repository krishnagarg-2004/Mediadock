"""Unit tests for the MediaCore event coordinator."""

import sys
import threading
import unittest
from unittest.mock import MagicMock

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from src.core.models import TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider
from src.core.media_core import MediaCore


class DummyProvider(BaseMediaProvider):
    """Dummy BaseMediaProvider subclass for testing MediaCore callback wiring."""

    def __init__(self) -> None:
        self.is_active = False
        self.track_cb = None
        self.status_cb = None
        self.session_cb = None
        self.current_track = TrackInfo(title="Test Track", artist="Test Artist")
        self.current_status = PlaybackStatus.PLAYING

    def get_current_track(self) -> TrackInfo:
        return self.current_track

    def get_playback_status(self) -> PlaybackStatus:
        return self.current_status

    def is_session_available(self) -> bool:
        return True

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



class TestMediaCore(unittest.TestCase):
    """Test suite for MediaCore signal emissions, lifecycle, and provider delegation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a QApplication instance exists for PySide6 Signal/QObject testing."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_media_core_initialization(self) -> None:
        """Verify MediaCore wires callbacks on provider upon instantiation."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)

        self.assertIsNotNone(provider.track_cb)
        self.assertIsNotNone(provider.status_cb)
        self.assertIsNotNone(provider.session_cb)

    def test_getter_delegation(self) -> None:
        """Verify getters delegate cleanly to the underlying provider."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)

        self.assertEqual(core.get_current_track(), provider.current_track)
        self.assertEqual(core.get_playback_status(), provider.current_status)
        self.assertTrue(core.is_session_available())

    def test_lifecycle_delegation(self) -> None:
        """Verify start() and stop() delegate to the underlying provider."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)

        core.start()
        self.assertTrue(provider.is_active)

        core.stop()
        self.assertFalse(provider.is_active)

    def test_track_changed_signal_emission(self) -> None:
        """Verify track_changed Qt Signal is emitted when provider callback triggers."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)

        mock_slot = MagicMock()
        core.track_changed.connect(mock_slot)

        new_track = TrackInfo(title="New Song", artist="New Artist")
        provider.track_cb(new_track)

        mock_slot.assert_called_once_with(new_track)

    def test_playback_status_changed_signal_emission(self) -> None:
        """Verify playback_status_changed Qt Signal is emitted when provider callback triggers."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)

        mock_slot = MagicMock()
        core.playback_status_changed.connect(mock_slot)

        provider.status_cb(PlaybackStatus.PAUSED)

        mock_slot.assert_called_once_with(PlaybackStatus.PAUSED)

    def test_session_availability_changed_signal_emission(self) -> None:
        """Verify session_availability_changed Qt Signal is emitted when provider callback triggers."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)

        mock_slot = MagicMock()
        core.session_availability_changed.connect(mock_slot)

        provider.session_cb(False)

        mock_slot.assert_called_once_with(False)

    def test_cross_thread_signal_delivery(self) -> None:
        """Verify provider callback invoked on a background thread emits signal safely to main thread."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)

        received_tracks = []

        def on_track(track: TrackInfo) -> None:
            received_tracks.append(track)

        core.track_changed.connect(on_track)

        bg_track = TrackInfo(title="Background Song", artist="Worker Thread")

        def bg_worker() -> None:
            provider.track_cb(bg_track)

        worker = threading.Thread(target=bg_worker, daemon=True)
        worker.start()
        worker.join(timeout=2.0)

        # Process queued Qt events on the main GUI thread
        QCoreApplication.processEvents()

        self.assertEqual(len(received_tracks), 1)
        self.assertEqual(received_tracks[0], bg_track)


if __name__ == "__main__":
    unittest.main()
