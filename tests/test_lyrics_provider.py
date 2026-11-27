"""Unit tests for Synchronized Lyrics Provider, metadata sanitization, and LRC parsing."""

import json
import unittest
from unittest.mock import MagicMock, patch
from src.media.lyrics_provider import (
    LyricsProvider,
    LyricsLine,
    sanitize_metadata,
)


class TestLyricsProvider(unittest.TestCase):
    def setUp(self):
        self.provider = LyricsProvider()

    def test_parse_lrc_valid_lines(self):
        lrc = (
            "[00:04.50]First line of song\n"
            "[00:12.80]Second line of song\n"
            "[01:05.123]Chorus line here\n"
        )
        lines = LyricsProvider._parse_lrc(lrc)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0].time_ms, 4500)
        self.assertEqual(lines[0].text, "First line of song")
        self.assertEqual(lines[1].time_ms, 12800)
        self.assertEqual(lines[1].text, "Second line of song")
        self.assertEqual(lines[2].time_ms, 65123)
        self.assertEqual(lines[2].text, "Chorus line here")

    def test_parse_lrc_repeated_tags_and_metadata_headers(self):
        lrc = (
            "[ar:Sample Artist]\n"
            "[ti:Sample Title]\n"
            "[al:Sample Album]\n"
            "[00:10.00][00:20.00]Repeated hook line\n"
            "[00:30.5]Short millis line\n"
        )
        lines = LyricsProvider._parse_lrc(lrc)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0].time_ms, 10000)
        self.assertEqual(lines[0].text, "Repeated hook line")
        self.assertEqual(lines[1].time_ms, 20000)
        self.assertEqual(lines[1].text, "Repeated hook line")
        self.assertEqual(lines[2].time_ms, 30500)
        self.assertEqual(lines[2].text, "Short millis line")

    def test_get_current_lyric_timeline_matching(self):
        lrc = (
            "[00:05.00]Intro line\n"
            "[00:15.00]Verse 1 line\n"
            "[00:30.00]Chorus line\n"
        )
        self.provider._cached_lines = LyricsProvider._parse_lrc(lrc)
        self.assertTrue(self.provider.has_synced_lyrics())

        # Before first lyric
        self.assertIsNone(self.provider.get_current_lyric(2000))

        # During Intro line
        self.assertEqual(self.provider.get_current_lyric(5000), "Intro line")
        self.assertEqual(self.provider.get_current_lyric(12000), "Intro line")

        # During Verse 1 line
        self.assertEqual(self.provider.get_current_lyric(15000), "Verse 1 line")
        self.assertEqual(self.provider.get_current_lyric(25000), "Verse 1 line")

        # During Chorus line
        self.assertEqual(self.provider.get_current_lyric(30000), "Chorus line")
        self.assertEqual(self.provider.get_current_lyric(50000), "Chorus line")

    def test_sanitize_metadata_remaster_and_video_noise(self):
        test_cases = [
            ("In the End - 2020 Remaster", "Linkin Park", "In the End", "Linkin Park"),
            ("Hotel California - 2013 Remaster", "Eagles", "Hotel California", "Eagles"),
            ("Smells Like Teen Spirit (Remastered 2011)", "Nirvana", "Smells Like Teen Spirit", "Nirvana"),
            ("Starboy - Club Mix", "The Weeknd", "Starboy", "The Weeknd"),
            ("Shape of You (Official Music Video)", "Ed Sheeran", "Shape of You", "Ed Sheeran"),
            ("Blinding Lights [Official Audio]", "The Weeknd", "Blinding Lights", "The Weeknd"),
            ("Levitating (feat. DaBaby)", "Dua Lipa", "Levitating", "Dua Lipa"),
            ("Bad Guy - Radio Edit", "Billie Eilish", "Bad Guy", "Billie Eilish"),
        ]
        for raw_title, raw_artist, exp_title, exp_artist in test_cases:
            title, artist = sanitize_metadata(raw_title, raw_artist)
            self.assertEqual(title, exp_title, f"Failed title sanitization for: {raw_title}")
            self.assertEqual(artist, exp_artist, f"Failed artist sanitization for: {raw_artist}")

    def test_sanitize_metadata_browser_youtube_format(self):
        # YouTube / browser title format: "Artist - Song Title (Video)"
        title, artist = sanitize_metadata("Queen - Bohemian Rhapsody (Official Video)", "YouTube")
        self.assertEqual(title, "Bohemian Rhapsody")
        self.assertEqual(artist, "Queen")

        title2, artist2 = sanitize_metadata("Coldplay - Yellow", "Google Chrome")
        self.assertEqual(title2, "Yellow")
        self.assertEqual(artist2, "Coldplay")

    def test_fetch_lyrics_async_cached_callback(self):
        callback = MagicMock()
        provider = LyricsProvider(on_lyrics_loaded=callback)
        provider._cached_track_key = "coldplay - yellow"
        provider._cached_lines = [LyricsLine(5000, "Look at the stars")]

        provider.fetch_lyrics_async("Yellow", "Coldplay", 260000)
        callback.assert_called_once_with("coldplay - yellow", True)

    def test_fetch_lyrics_multi_tier_fallback(self):
        provider = LyricsProvider()

        # Mock _http_get_json to return 404/None on raw /api/get, and return result on /api/search
        def fake_http_get(url, timeout=3.5):
            if "api/get" in url:
                return None
            if "api/search" in url:
                return [
                    {
                        "id": 1,
                        "trackName": "In The End",
                        "artistName": "Linkin Park",
                        "duration": 216,
                        "syncedLyrics": "[00:15.00]It starts with one thing\n[00:18.00]I don't know why",
                    }
                ]
            return None

        with patch.object(LyricsProvider, "_http_get_json", side_effect=fake_http_get):
            provider._current_fetch_id = 1
            provider._worker_fetch(1, "linkin park - in the end", "In the End - 2020 Remaster", "Linkin Park", 216000)

        self.assertTrue(provider.has_synced_lyrics())
        self.assertEqual(provider.get_current_lyric(16000), "It starts with one thing")
        self.assertEqual(provider.get_current_lyric(20000), "I don't know why")

    def test_fetch_superseded_worker_discards_stale_result(self):
        callback = MagicMock()
        provider = LyricsProvider(on_lyrics_loaded=callback)

        # Set provider._current_fetch_id to 2 (simulating Track 2 request arrived)
        provider._current_fetch_id = 2

        # Worker for Track 1 finishes with fetch_id 1
        with patch.object(provider, "_try_api_get", return_value=("[00:01.00]Old track", None)):
            provider._worker_fetch(1, "artist a - track a", "Track A", "Artist A", 180000)

        # Result from fetch_id 1 must be discarded
        self.assertFalse(provider.has_synced_lyrics())
        self.assertIsNone(provider._cached_track_key)
        callback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
