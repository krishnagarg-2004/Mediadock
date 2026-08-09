"""Unit tests for the GSMTCProvider media detection implementation."""

import asyncio
import threading
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

from src.core.models import TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider
from src.media.gsmtc_provider import GSMTCProvider


class TestGSMTCProvider(unittest.TestCase):
    """Test suite for GSMTCProvider lifecycle, callbacks, and event semantics."""

    def test_inheritance(self) -> None:
        """Verify GSMTCProvider inherits from BaseMediaProvider."""
        provider = GSMTCProvider()
        self.assertIsInstance(provider, BaseMediaProvider)

    def test_initial_default_state(self) -> None:
        """Verify initial no-session default state."""
        provider = GSMTCProvider()
        self.assertEqual(provider.get_current_track(), TrackInfo.empty())
        self.assertEqual(provider.get_playback_status(), PlaybackStatus.CLOSED)
        self.assertFalse(provider.is_session_available())

    def test_callback_setters(self) -> None:
        """Verify callback registration setters update internal callbacks."""
        provider = GSMTCProvider()

        track_cb = MagicMock()
        status_cb = MagicMock()
        session_cb = MagicMock()

        provider.set_on_track_changed(track_cb)
        provider.set_on_status_changed(status_cb)
        provider.set_on_session_availability_changed(session_cb)

        self.assertEqual(provider._on_track_changed_cb, track_cb)
        self.assertEqual(provider._on_status_changed_cb, status_cb)
        self.assertEqual(provider._on_session_availability_changed_cb, session_cb)

    def test_repeated_stop_listening(self) -> None:
        """Verify stop_listening() is idempotent and safe when called repeatedly."""
        provider = GSMTCProvider()
        provider.stop_listening()
        provider.stop_listening()
        provider.stop_listening()
        self.assertFalse(provider._is_listening)

    @patch("src.media.gsmtc_provider.WINRT_AVAILABLE", True)
    @patch("src.media.gsmtc_provider.media_control")
    def test_startup_failure_graceful_handling(self, mock_media_control) -> None:
        """Verify startup failure cleans up background loop and thread cleanly."""
        mock_media_control.GlobalSystemMediaTransportControlsSessionManager.request_async = AsyncMock(
            side_effect=RuntimeError("WinRT API connection error")
        )

        provider = GSMTCProvider()
        provider.start_listening()

        self.assertFalse(provider._is_listening)
        self.assertIsNone(provider._thread)
        self.assertIsNone(provider._loop)

    def test_duplicate_track_event_suppression(self) -> None:
        """Verify duplicate track info events are suppressed without calling callbacks."""
        track_cb = MagicMock()
        provider = GSMTCProvider(on_track_changed=track_cb)

        t1 = TrackInfo(title="Song A", artist="Artist A", position_ms=100)
        t2 = TrackInfo(title="Song A", artist="Artist A", position_ms=200)  # Position change only

        provider._update_track_info(t1)
        self.assertEqual(track_cb.call_count, 1)

        # Updating with t2 (position change only) must NOT fire callback
        provider._update_track_info(t2)
        self.assertEqual(track_cb.call_count, 1)

    def test_duplicate_status_event_suppression(self) -> None:
        """Verify duplicate status events are suppressed without calling callbacks."""
        status_cb = MagicMock()
        provider = GSMTCProvider(on_status_changed=status_cb)

        provider._update_playback_status(PlaybackStatus.PLAYING)
        self.assertEqual(status_cb.call_count, 1)

        # Updating with same status must NOT fire callback
        provider._update_playback_status(PlaybackStatus.PLAYING)
        self.assertEqual(status_cb.call_count, 1)

        provider._update_playback_status(PlaybackStatus.PAUSED)
        self.assertEqual(status_cb.call_count, 2)

    def test_session_availability_callback(self) -> None:
        """Verify session availability callback fires on transition."""
        session_cb = MagicMock()
        provider = GSMTCProvider(on_session_availability_changed=session_cb)

        provider._update_session_availability(True)
        session_cb.assert_called_once_with(True)

        # Duplicate state must not fire callback
        provider._update_session_availability(True)
        self.assertEqual(session_cb.call_count, 1)

        provider._update_session_availability(False)
        self.assertEqual(session_cb.call_count, 2)
        session_cb.assert_called_with(False)

    def test_session_identity_comparison(self) -> None:
        """Verify session identity comparison uses app_id or reference equality."""
        provider = GSMTCProvider()

        s1 = MagicMock()
        s1.source_app_user_model_id = "Spotify.exe"

        s2 = MagicMock()
        s2.source_app_user_model_id = "Spotify.exe"

        s3 = MagicMock()
        s3.source_app_user_model_id = "Chrome.exe"

        self.assertTrue(provider._is_same_session(s1, s2))
        self.assertFalse(provider._is_same_session(s1, s3))
        self.assertFalse(provider._is_same_session(s1, None))
        self.assertTrue(provider._is_same_session(None, None))

    def test_playback_status_mapping(self) -> None:
        """Verify WinRT status objects, names, and integers map to domain PlaybackStatus enums."""
        provider = GSMTCProvider()

        # String mappings
        self.assertEqual(provider._map_playback_status("PLAYING"), PlaybackStatus.PLAYING)
        self.assertEqual(provider._map_playback_status("PAUSED"), PlaybackStatus.PAUSED)
        self.assertEqual(provider._map_playback_status("STOPPED"), PlaybackStatus.STOPPED)
        self.assertEqual(provider._map_playback_status("CLOSED"), PlaybackStatus.CLOSED)
        self.assertEqual(provider._map_playback_status("INVALID"), PlaybackStatus.UNKNOWN)
        self.assertEqual(provider._map_playback_status(None), PlaybackStatus.UNKNOWN)

        # PyWinRT / enum integer value mappings (4=PLAYING, 5=PAUSED, 3=STOPPED, 1=CLOSED)
        self.assertEqual(provider._map_playback_status(4), PlaybackStatus.PLAYING)
        self.assertEqual(provider._map_playback_status(5), PlaybackStatus.PAUSED)
        self.assertEqual(provider._map_playback_status(3), PlaybackStatus.STOPPED)
        self.assertEqual(provider._map_playback_status(1), PlaybackStatus.CLOSED)

        # Mock enum objects with .name and .value properties
        mock_playing = MagicMock()
        mock_playing.name = "PLAYING"
        mock_playing.value = 4
        self.assertEqual(provider._map_playback_status(mock_playing), PlaybackStatus.PLAYING)

        mock_paused = MagicMock()
        mock_paused.name = "PAUSED"
        mock_paused.value = 5
        self.assertEqual(provider._map_playback_status(mock_paused), PlaybackStatus.PAUSED)

    def test_thread_lifecycle_start_stop(self) -> None:
        """Verify background worker thread starts and joins cleanly."""
        provider = GSMTCProvider()
        # Mock _async_start to avoid native WinRT calls in pure unit test
        provider._async_start = AsyncMock()

        provider.start_listening()
        self.assertTrue(provider._is_listening)
        self.assertIsNotNone(provider._thread)
        self.assertTrue(provider._thread.is_alive())

        provider.stop_listening()
        self.assertFalse(provider._is_listening)
        self.assertIsNone(provider._thread)
        self.assertIsNone(provider._loop)


if __name__ == "__main__":
    unittest.main()
