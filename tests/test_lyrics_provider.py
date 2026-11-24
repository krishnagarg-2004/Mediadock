"""Unit tests for Synchronized Lyrics Provider and LRC Parser."""

import unittest
from src.media.lyrics_provider import LyricsProvider, LyricsLine


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

    def test_get_current_lyric_timeline_matching(self):
        lrc = (
            "[00:05.00]Intro line\n"
            "[00:15.00]Verse 1 line\n"
            "[00:30.00]Chorus line\n"
        )
        self.provider._cached_lines = LyricsProvider._parse_lrc(lrc)

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


if __name__ == "__main__":
    unittest.main()
