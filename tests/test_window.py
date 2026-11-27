"""Unit tests for MediaDock window initialization and configuration."""

import sys
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.frameless_window import FramelessWindow


class TestMediaDockWindow(unittest.TestCase):
    """Test suite verifying window flags, translucent background, and initialization."""

    @classmethod
    def setUpClass(cls) -> None:
        """Ensure a QApplication instance exists for testing GUI components."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self) -> None:
        from src.core.settings import SettingsManager
        SettingsManager().set_lyrics_enabled(True)

    def tearDown(self) -> None:
        from src.core.settings import SettingsManager
        SettingsManager().set_lyrics_enabled(True)

    def test_frameless_window_flags(self) -> None:
        """Verify FramelessWindow initializes with correct Qt window flags."""
        window = FramelessWindow()
        flags = window.windowFlags()

        self.assertTrue(flags & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(flags & Qt.WindowType.WindowStaysOnTopHint)
        self.assertTrue(flags & Qt.WindowType.Tool)

    def test_translucent_background_attribute(self) -> None:
        """Verify WA_TranslucentBackground attribute is enabled."""
        window = FramelessWindow()
        self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))

    def test_main_window_properties(self) -> None:
        """Verify MainWindow default properties and EXPANDED dimensions."""
        from src.ui.main_window import DynamicIslandState, EXPANDED_SIZE
        window = MainWindow()
        self.assertEqual(window.windowTitle(), "MediaDock")
        window.set_state(DynamicIslandState.EXPANDED)
        self.assertEqual(window.width(), EXPANDED_SIZE[0])
        self.assertEqual(window.height(), EXPANDED_SIZE[1])

    def test_artwork_label_dimensions(self) -> None:
        """Verify art_label fixed dimensions (92x92) and default pixmap match DeskNotch tile art."""
        window = MainWindow()
        self.assertEqual(window.art_label.width(), 92)
        self.assertEqual(window.art_label.height(), 92)
        self.assertEqual(window._default_art_pixmap.width(), 92)
        self.assertEqual(window._default_art_pixmap.height(), 92)

    def test_close_event_hides_window_when_close_to_tray_enabled(self) -> None:
        """Verify closeEvent ignores close and calls hide() when close_to_tray setting is True."""
        from unittest.mock import MagicMock
        from PySide6.QtGui import QCloseEvent
        from src.core.settings import SettingsManager

        mock_settings = MagicMock(spec=SettingsManager)
        mock_settings.get_close_to_tray.return_value = True
        mock_settings.get_always_on_top.return_value = True
        mock_settings.get_compact_mode.return_value = False

        window = MainWindow(settings_manager=mock_settings)
        window.show()

        event = QCloseEvent()
        window.closeEvent(event)

        self.assertFalse(event.isAccepted())
        self.assertFalse(window.isVisible())

    def test_close_event_quits_app_when_close_to_tray_disabled(self) -> None:
        """Verify closeEvent accepts event and calls QApplication.quit when close_to_tray is False."""
        from unittest.mock import MagicMock, patch
        from PySide6.QtGui import QCloseEvent
        from src.core.settings import SettingsManager

        mock_settings = MagicMock(spec=SettingsManager)
        mock_settings.get_close_to_tray.return_value = False
        mock_settings.get_always_on_top.return_value = True
        mock_settings.get_compact_mode.return_value = False

        window = MainWindow(settings_manager=mock_settings)

        event = QCloseEvent()
        with patch.object(QApplication, "quit") as mock_quit:
            window.closeEvent(event)
            self.assertTrue(event.isAccepted())
            mock_quit.assert_called_once()

    def test_toggle_window_visibility_logic(self) -> None:
        """Verify showing and hiding window toggles isVisible state cleanly."""
        window = MainWindow()

        window.show()
        self.assertTrue(window.isVisible())

        window.hide()
        self.assertFalse(window.isVisible())

        window.show()
        self.assertTrue(window.isVisible())

    def test_expanded_controls_stay_inside_media_tile_and_lyrics_render_full_width(self) -> None:
        """Verify transport buttons never clip outside MediaTile and lyrics render in dedicated full-width strip."""
        from src.ui.main_window import DynamicIslandState, EXPANDED_SIZE, LYRICS_BAR_EXTRA_HEIGHT

        window = MainWindow()
        window.set_state(DynamicIslandState.EXPANDED, animate=False)
        self.app.processEvents()

        # Without lyrics, height matches base EXPANDED_SIZE
        self.assertTrue(window.lyrics_label.isHidden())
        self.assertEqual(window.size().width(), EXPANDED_SIZE[0])
        self.assertEqual(window.size().height(), EXPANDED_SIZE[1])

        # Populate a long synced lyric line and trigger visibility
        window.lyrics_label.setText("♪ Just the same way you showed me, show me everything tonight")
        window.lyrics_label.show()
        window._sync_expanded_geometry()
        self.app.processEvents()

        self.assertEqual(window.height(), EXPANDED_SIZE[1] + LYRICS_BAR_EXTRA_HEIGHT)
        self.assertTrue(window.lyrics_label.wordWrap())
        self.assertIsNot(window.lyrics_label.parent(), window._media_tile_frame)
        self.assertGreaterEqual(window.lyrics_label.width(), 350)

        # Play/Pause disc and Prev/Next buttons stay strictly inside MediaTile bottom edge
        tile_rect = window._media_tile_frame.rect()
        self.assertLessEqual(window.btn_play_pause.geometry().bottom(), tile_rect.bottom())
        self.assertLessEqual(window.btn_prev.geometry().bottom(), tile_rect.bottom())
        self.assertLessEqual(window.btn_next.geometry().bottom(), tile_rect.bottom())

    def test_capsule_collapsed_and_oval_expanded_geometry(self) -> None:
        """Verify collapsed uses flush top-bezel notch (y=0, flared ears) while expanded keeps floating oval shape."""
        from src.ui.main_window import DynamicIslandState, COLLAPSED_TOP_OFFSET_PX, EXPANDED_TOP_OFFSET_PX

        window = MainWindow()
        self.assertEqual(COLLAPSED_TOP_OFFSET_PX, 0)
        self.assertEqual(EXPANDED_TOP_OFFSET_PX, 12)
        window.set_state(DynamicIslandState.COLLAPSED, animate=False)
        self.assertEqual(window._border_radius, 14.0)
        self.assertEqual(window._ear_radius, 8.0)

        window.set_state(DynamicIslandState.EXPANDED, animate=False)
        self.assertEqual(window._border_radius, 32.0)
        self.assertEqual(window._ear_radius, 0.0)

    def test_lyrics_loaded_signal_updates_ui_and_geometry(self) -> None:
        """Verify lyrics_loaded_signal updates lyrics_label text and geometry in expanded mode."""
        from src.core.models import TrackInfo
        from src.media.lyrics_provider import LyricsLine
        from src.ui.main_window import DynamicIslandState, EXPANDED_SIZE, LYRICS_BAR_EXTRA_HEIGHT

        window = MainWindow()
        window.set_state(DynamicIslandState.EXPANDED, animate=False)
        self.app.processEvents()

        track = TrackInfo(
            title="In the End",
            artist="Linkin Park",
            duration_ms=216000,
            position_ms=16000,
        )
        window.on_track_changed(track)
        self.app.processEvents()

        # Mock cached lines in provider
        window._lyrics_provider._cached_track_key = "linkin park - in the end"
        window._lyrics_provider._cached_lines = [
            LyricsLine(10000, "It starts with one thing"),
            LyricsLine(18000, "I don't know why"),
        ]

        # Emit loaded signal
        window.lyrics_loaded_signal.emit("linkin park - in the end", True)
        self.app.processEvents()

        self.assertFalse(window.lyrics_label.isHidden())
        self.assertIn("It starts with one thing", window.lyrics_label.text())
        self.assertEqual(window.height(), EXPANDED_SIZE[1] + LYRICS_BAR_EXTRA_HEIGHT)

        # Disable lyrics in settings
        window._settings_manager.set_lyrics_enabled(False)
        window._on_setting_changed("features/lyrics_enabled", False)
        self.app.processEvents()

        self.assertTrue(window.lyrics_label.isHidden())
        self.assertEqual(window.height(), EXPANDED_SIZE[1])


if __name__ == "__main__":
    unittest.main()
