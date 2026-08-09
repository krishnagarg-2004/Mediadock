"""Integration unit tests for Step 5: MainWindow UI integration with MediaCore."""

import sys
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.core.models import TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider
from src.core.media_core import MediaCore
from src.ui.main_window import MainWindow


class DummyProvider(BaseMediaProvider):
    """Dummy BaseMediaProvider subclass for Step 5 integration testing."""

    def __init__(self) -> None:
        self.is_active = False
        self.track_cb = None
        self.status_cb = None
        self.session_cb = None
        self.current_track = TrackInfo(title="Initial Title", artist="Initial Artist")
        self.current_status = PlaybackStatus.PAUSED

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


class TestStep5Integration(unittest.TestCase):
    """Test suite verifying MainWindow UI updates when connected to MediaCore."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a QApplication instance exists for PySide6 GUI testing."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_window_frameless_properties_preserved(self) -> None:
        """Verify MainWindow retains frameless, translucent, and always-on-top flags."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        flags = window.windowFlags()
        self.assertTrue(flags & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(flags & Qt.WindowType.WindowStaysOnTopHint)
        self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))

    def test_initial_sync_display(self) -> None:
        """Verify MainWindow populates initial track and status on creation."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        self.assertEqual(window.title_label.text(), "Initial Title")
        self.assertEqual(window.artist_label.text(), "Initial Artist")
        self.assertEqual(window.status_label.text(), "PAUSED")

    def test_track_changed_slot_updates_ui(self) -> None:
        """Verify emitting track_changed updates labels in MainWindow."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        new_track = TrackInfo(
            title="Die With A Smile",
            artist="Lady Gaga & Bruno Mars",
            album="Single",
        )
        core.track_changed.emit(new_track)

        self.assertEqual(window.title_label.text(), "Die With A Smile")
        self.assertEqual(window.artist_label.text(), "Lady Gaga & Bruno Mars")

    def test_playback_status_changed_slot_updates_badge(self) -> None:
        """Verify emitting playback_status_changed updates status badge in MainWindow."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        core.playback_status_changed.emit(PlaybackStatus.PLAYING)
        self.assertEqual(window.status_label.text(), "PLAYING")

        core.playback_status_changed.emit(PlaybackStatus.STOPPED)
        self.assertEqual(window.status_label.text(), "STOPPED")

    def test_session_availability_fallback(self) -> None:
        """Verify emitting session_availability_changed(False) resets UI to empty state."""
        provider = DummyProvider()
        core = MediaCore(provider=provider)
        window = MainWindow(media_core=core)

        core.session_availability_changed.emit(False)

        self.assertEqual(window.title_label.text(), "No Media Playing")
        self.assertEqual(window.artist_label.text(), "Unknown Artist")
        self.assertEqual(window.status_label.text(), "CLOSED")


if __name__ == "__main__":
    unittest.main()
