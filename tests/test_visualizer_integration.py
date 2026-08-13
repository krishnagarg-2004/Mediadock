"""Unit and integration test suite for real-time Audio Visualizer UI integration and WASAPI wiring."""

import sys
import unittest
from unittest.mock import MagicMock
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from src.core.models import TrackInfo, PlaybackStatus, VolumeState
from src.media.audio_capture import AudioFrame
from src.media.audio_analyzer import AudioAnalyzer
from src.ui.components_island import ReactiveVisualizerWidget
from src.ui.main_window import MainWindow
from src.core.media_core import MediaCore


class TestVisualizerIntegration(unittest.TestCase):
    """Test suite covering real-time visualizer UI updates, zero artificial animation, and MediaCore signal dispatch."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a single QApplication instance exists for Qt widget tests."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_reactive_visualizer_realtime_bar_setting(self) -> None:
        """Verify ReactiveVisualizerWidget stores real-time bar heights and sets animated state."""
        visualizer = ReactiveVisualizerWidget(bar_count=5)
        self.assertFalse(visualizer.is_animated)

        # Set status to PLAYING
        visualizer.set_playback_status(PlaybackStatus.PLAYING)
        self.assertFalse(visualizer.is_animated)  # No real-time bars yet

        # Set real-time bar heights
        bar_data = [0.1, 0.4, 0.9, 0.3, 0.2]
        visualizer.set_bar_heights(bar_data)
        self.assertTrue(visualizer.is_animated)
        self.assertEqual(visualizer._realtime_bars, bar_data)

    def test_no_artificial_timer_animation(self) -> None:
        """Verify ReactiveVisualizerWidget does NOT run artificial animation timers."""
        visualizer = ReactiveVisualizerWidget(bar_count=5)
        self.assertFalse(hasattr(visualizer, "_anim_timer") and visualizer._anim_timer.isActive())

        visualizer.set_playback_status(PlaybackStatus.PLAYING)
        self.assertFalse(hasattr(visualizer, "_anim_timer") and visualizer._anim_timer.isActive())

        visualizer.set_playback_status(PlaybackStatus.PAUSED)
        self.assertFalse(hasattr(visualizer, "_anim_timer") and visualizer._anim_timer.isActive())

    def test_clear_bar_heights_on_pause(self) -> None:
        """Verify pausing or clearing bar heights restores visualizer to static baseline state."""
        visualizer = ReactiveVisualizerWidget(bar_count=5)
        visualizer.set_playback_status(PlaybackStatus.PLAYING)
        visualizer.set_bar_heights([0.8, 0.8, 0.8, 0.8, 0.8])
        self.assertTrue(visualizer.is_animated)

        # Clear bar heights
        visualizer.clear_bar_heights()
        self.assertFalse(visualizer.is_animated)
        self.assertIsNone(visualizer._realtime_bars)

        # Pause playback
        visualizer.set_playback_status(PlaybackStatus.PLAYING)
        visualizer.set_bar_heights([0.5, 0.5, 0.5, 0.5, 0.5])
        visualizer.set_playback_status(PlaybackStatus.PAUSED)
        self.assertFalse(visualizer.is_animated)
        self.assertIsNone(visualizer._realtime_bars)

    def test_mediacore_audio_frame_signal_emission(self) -> None:
        """Verify MediaCore receives AudioFrame from audio capture and emits audio_visualizer_updated signal."""
        mock_provider = MagicMock()
        mock_volume_provider = MagicMock()
        mock_capture = MagicMock()
        analyzer = AudioAnalyzer(bar_count=5)

        media_core = MediaCore(
            provider=mock_provider,
            volume_provider=mock_volume_provider,
            audio_capture=mock_capture,
            analyzer=analyzer,
        )

        signal_received = []
        media_core.audio_visualizer_updated.connect(lambda bars: signal_received.append(bars))

        # Simulate audio frame callback from capture layer
        frame = AudioFrame(samples=[0.8] * 500, sample_rate=48000, channels=2, frame_count=250)
        media_core._on_provider_audio_frame(frame)

        self.assertEqual(len(signal_received), 1)
        self.assertEqual(len(signal_received[0]), 5)
        self.assertTrue(all(b > 0.3 for b in signal_received[0]))

    def test_mainwindow_audio_visualizer_slot_integration(self) -> None:
        """Verify MainWindow receives audio_visualizer_updated signal and updates ReactiveVisualizerWidget during PLAYING status."""
        mock_core = MagicMock()
        mock_core.get_current_track.return_value = TrackInfo("Title", "Artist", "Album", None, "Spotify.exe", 100000, 0)
        mock_core.get_playback_status.return_value = PlaybackStatus.PLAYING
        mock_core.is_session_available.return_value = True
        mock_core.get_volume_state.return_value = MagicMock(is_supported=True, volume_percent=50, is_muted=False)
        mock_core.get_active_session_info.return_value = None

        window = MainWindow(media_core=mock_core)
        window.on_status_changed(PlaybackStatus.PLAYING)

        # Emit simulated bars
        bars = [0.2, 0.5, 0.8, 0.4, 0.1]
        window.on_audio_visualizer_updated(bars)

        self.assertEqual(window._visualizer._realtime_bars, bars)

        # Transition to PAUSED -> bars must clear
        window.on_status_changed(PlaybackStatus.PAUSED)
        self.assertIsNone(window._visualizer._realtime_bars)


if __name__ == "__main__":
    unittest.main()
