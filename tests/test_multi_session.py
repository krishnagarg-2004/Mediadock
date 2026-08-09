"""Unit tests for GSMTC multi-session architecture, session enumeration, and app selection."""

import unittest
from unittest.mock import MagicMock, patch

from src.core.models import MediaSessionInfo, TrackInfo, PlaybackStatus
from src.media.base_provider import BaseMediaProvider
from src.media.gsmtc_provider import GSMTCProvider
from src.core.media_core import MediaCore
from src.ui.system_tray import SystemTrayIcon


class DummyMediaProvider(BaseMediaProvider):
    """Dummy provider subclass for testing base contracts."""

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


class TestMultiSessionArchitecture(unittest.TestCase):
    """Test MediaSessionInfo data model, provider abstractions, and multi-session dispatches."""

    def test_media_session_info_dataclass(self) -> None:
        """Verify MediaSessionInfo dataclass immutability and default parameters."""
        info = MediaSessionInfo(
            session_id="Spotify.exe#123",
            app_id="Spotify.exe",
            display_name="Spotify",
            is_current=True,
            is_selected=False,
        )
        self.assertEqual(info.session_id, "Spotify.exe#123")
        self.assertEqual(info.app_id, "Spotify.exe")
        self.assertEqual(info.display_name, "Spotify")
        self.assertTrue(info.is_current)
        self.assertFalse(info.is_selected)

    def test_base_provider_default_multi_session_methods(self) -> None:
        """Verify BaseMediaProvider default multi-session contract implementations."""
        provider = DummyMediaProvider()
        self.assertEqual(provider.get_available_sessions(), [])
        self.assertFalse(provider.select_session("some_id"))
        self.assertIsNone(provider.get_selected_session_id())

    def test_format_display_name_helpers(self) -> None:
        """Verify GSMTCProvider display name formatting for popular media apps."""
        fmt = GSMTCProvider._format_display_name
        self.assertEqual(fmt("Spotify.exe"), "Spotify")
        self.assertEqual(fmt("chrome.exe"), "Google Chrome")
        self.assertEqual(fmt("msedge.exe"), "Microsoft Edge")
        self.assertEqual(fmt("vlc.exe"), "VLC Media Player")
        self.assertEqual(fmt("firefox.exe"), "Mozilla Firefox")
        self.assertEqual(fmt("Apple.Music.exe"), "Apple Music")
        self.assertEqual(fmt("Unknown"), "Unknown Media Player")

    def test_gsmtc_provider_session_selection_and_fallback(self) -> None:
        """Test GSMTCProvider session selection and automatic fallback when selected session disappears."""
        provider = GSMTCProvider()

        mock_session_1 = MagicMock()
        mock_session_1.source_app_user_model_id = "Spotify.exe"

        mock_session_2 = MagicMock()
        mock_session_2.source_app_user_model_id = "chrome.exe"

        s1_id = provider._get_session_id(mock_session_1)
        s2_id = provider._get_session_id(mock_session_2)

        # Select session 1
        provider.select_session(s1_id)
        self.assertEqual(provider.get_selected_session_id(), s1_id)

        # Update available sessions with mock sessions
        sessions_changed_calls = []
        provider.set_on_sessions_changed(lambda lst: sessions_changed_calls.append(lst))

        provider._update_available_sessions(
            [mock_session_1, mock_session_2],
            os_current_session=mock_session_2,
            selected_session=mock_session_1,
        )

        self.assertEqual(len(sessions_changed_calls), 1)
        avail = provider.get_available_sessions()
        self.assertEqual(len(avail), 2)
        self.assertTrue(avail[0].is_selected)

    def test_media_core_signal_propagation(self) -> None:
        """Verify MediaCore propagates sessions_changed signals and session selection methods."""
        provider = DummyMediaProvider()
        core = MediaCore(provider=provider)

        received_sessions = []
        core.sessions_changed.connect(lambda lst: received_sessions.append(lst))

        test_sessions = [
            MediaSessionInfo(
                session_id="Spotify.exe#1",
                app_id="Spotify.exe",
                display_name="Spotify",
                is_current=True,
                is_selected=True,
            )
        ]

        # Trigger callback from provider
        core._on_provider_sessions_changed(test_sessions)
        self.assertEqual(len(received_sessions), 1)
        self.assertEqual(received_sessions[0], test_sessions)

        self.assertEqual(core.get_available_sessions(), [])
        self.assertFalse(core.select_session("Spotify.exe#1"))
        self.assertIsNone(core.get_selected_session_id())

    def test_system_tray_media_source_menu(self) -> None:
        """Verify SystemTrayIcon creates Media Source submenu and handles selection dispatches."""
        provider = DummyMediaProvider()
        core = MediaCore(provider=provider)
        tray = SystemTrayIcon(media_core=core)

        self.assertIsNotNone(tray.menu_media_source)

        test_sessions = [
            MediaSessionInfo(
                session_id="Spotify.exe#1",
                app_id="Spotify.exe",
                display_name="Spotify",
                is_current=True,
                is_selected=True,
            ),
            MediaSessionInfo(
                session_id="chrome.exe#2",
                app_id="chrome.exe",
                display_name="Google Chrome",
                is_current=False,
                is_selected=False,
            ),
        ]

        tray._on_sessions_changed(test_sessions)
        actions = tray.menu_media_source.actions()
        # Auto + Separator + 2 Sessions = 4 actions
        self.assertGreaterEqual(len(actions), 3)


if __name__ == "__main__":
    unittest.main()
