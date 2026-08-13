"""Unit tests for Dynamic Island UI presentation components (ReactiveVisualizerWidget & CollapsedCapsuleWidget)."""

import sys
import unittest
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from src.core.models import PlaybackStatus
from src.ui.components_island import ReactiveVisualizerWidget, CollapsedCapsuleWidget


class TestDynamicIslandComponents(unittest.TestCase):
    """Test suite for presentation-only Dynamic Island UI components."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure QApplication instance exists for Qt GUI testing."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_visualizer_creation_and_defaults(self) -> None:
        """Verify ReactiveVisualizerWidget initializes independently with default parameters."""
        vis = ReactiveVisualizerWidget(bar_count=5)
        self.assertIsNotNone(vis)
        self.assertFalse(vis.is_animated)

    def test_visualizer_playback_state_and_bars(self) -> None:
        """Verify visualizer receives bar heights during PLAYING and clears bars on PAUSED/STOPPED/CLOSED."""
        vis = ReactiveVisualizerWidget()

        # Start playing with real bar heights
        vis.set_playback_status(PlaybackStatus.PLAYING)
        vis.set_bar_heights([0.2, 0.4, 0.6, 0.8, 1.0])
        self.assertTrue(vis.is_animated)

        # Pause playback -> bars cleared
        vis.set_playback_status(PlaybackStatus.PAUSED)
        self.assertFalse(vis.is_animated)

        # Resume playing with string status and bar heights
        vis.set_playback_status("PLAYING")
        vis.set_bar_heights([0.5, 0.5, 0.5, 0.5, 0.5])
        self.assertTrue(vis.is_animated)

        # Stop playback -> bars cleared
        vis.set_playback_status(PlaybackStatus.STOPPED)
        self.assertFalse(vis.is_animated)

    def test_visualizer_no_artificial_animation_dependency(self) -> None:
        """Verify ReactiveVisualizerWidget renders cleanly with static baseline when no real audio bars are present."""
        vis = ReactiveVisualizerWidget(bar_count=4)
        vis.resize(60, 20)
        vis.set_playback_status(PlaybackStatus.PLAYING)
        # Verify repainting does not crash or raise exceptions
        vis.repaint()

    def test_capsule_creation_and_dimensions(self) -> None:
        """Verify CollapsedCapsuleWidget initializes independently with target 180x40 dimensions."""
        capsule = CollapsedCapsuleWidget()
        self.assertEqual(capsule.size(), QSize(180, 40))
        self.assertEqual(capsule.minimumSize(), QSize(180, 40))
        self.assertEqual(capsule.maximumSize(), QSize(180, 40))

    def test_capsule_content_updates(self) -> None:
        """Verify track title, app icon, status dot, and accent color update cleanly."""
        capsule = CollapsedCapsuleWidget()

        # Track title update
        capsule.set_track_title("Cayendo - Spotify")
        self.assertEqual(capsule.title_label.full_text(), "Cayendo - Spotify")

        # Custom app icon update
        dummy_pix = QPixmap(16, 16)
        dummy_pix.fill(QColor("#1DB954"))
        capsule.set_app_icon(dummy_pix)
        self.assertIsNotNone(capsule.icon_label.pixmap())

        # Status update
        capsule.set_playback_status(PlaybackStatus.PLAYING)

        # Accent color update
        capsule.set_accent_color(QColor("#1DB954"))
        capsule.repaint()


if __name__ == "__main__":
    unittest.main()
