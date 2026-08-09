"""Unit tests for domain data models (TrackInfo, PlaybackStatus)."""

import unittest
from dataclasses import FrozenInstanceError

from src.core.models import TrackInfo, PlaybackStatus


class TestMediaModels(unittest.TestCase):
    """Test suite for TrackInfo immutability and PlaybackStatus enum values."""

    def test_track_info_instantiation(self) -> None:
        """Verify TrackInfo holds custom metadata correctly."""
        sample_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        track = TrackInfo(
            title="Die With A Smile",
            artist="Lady Gaga & Bruno Mars",
            album="Single",
            album_art_bytes=sample_bytes,
            app_id="Spotify.exe",
            duration_ms=251000,
            position_ms=105000,
        )

        self.assertEqual(track.title, "Die With A Smile")
        self.assertEqual(track.artist, "Lady Gaga & Bruno Mars")
        self.assertEqual(track.album, "Single")
        self.assertEqual(track.album_art_bytes, sample_bytes)
        self.assertEqual(track.app_id, "Spotify.exe")
        self.assertEqual(track.duration_ms, 251000)
        self.assertEqual(track.position_ms, 105000)

    def test_track_info_immutability(self) -> None:
        """Verify TrackInfo is immutable and prevents property mutation."""
        track = TrackInfo(title="Test Song", artist="Test Artist")

        with self.assertRaises((FrozenInstanceError, AttributeError)):
            track.title = "Mutated Title"  # type: ignore[misc]

    def test_track_info_empty_factory(self) -> None:
        """Verify TrackInfo.empty() returns appropriate fallback representation."""
        empty_track = TrackInfo.empty()

        self.assertEqual(empty_track.title, "No Media Playing")
        self.assertEqual(empty_track.artist, "Unknown Artist")
        self.assertEqual(empty_track.album, "")
        self.assertIsNone(empty_track.album_art_bytes)
        self.assertEqual(empty_track.app_id, "")
        self.assertEqual(empty_track.duration_ms, 0)
        self.assertEqual(empty_track.position_ms, 0)

    def test_playback_status_enum(self) -> None:
        """Verify PlaybackStatus enum members and string representations."""
        self.assertEqual(PlaybackStatus.PLAYING.value, "PLAYING")
        self.assertEqual(PlaybackStatus.PAUSED.value, "PAUSED")
        self.assertEqual(PlaybackStatus.STOPPED.value, "STOPPED")
        self.assertEqual(PlaybackStatus.CLOSED.value, "CLOSED")
        self.assertEqual(PlaybackStatus.UNKNOWN.value, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
