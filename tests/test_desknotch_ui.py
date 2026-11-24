"""Unit tests for DeskNotch-inspired UI chassis, pin toggle, dock actions, and rounded art."""

import os
import sys
import tempfile
import unittest
from PySide6.QtCore import QBuffer, QByteArray, QEvent, QIODevice, QRectF, QSettings
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication

from src.core.models import PlaybackStatus, TrackInfo
from src.core.settings import SettingsManager
from src.ui.components_island import CollapsedNotchWidget
from src.ui.frameless_window import build_desknotch_path
from src.ui.main_window import DynamicIslandState, MainWindow
from src.ui.theme import create_rounded_pixmap


class TestDeskNotchUI(unittest.TestCase):
    """Test suite verifying DeskNotch visual shell, controls, pin state, and rounded artwork."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def _png_bytes(self, color: QColor) -> bytes:
        img = QImage(32, 32, QImage.Format.Format_RGB32)
        img.fill(color)
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        return bytes(ba)

    def test_build_desknotch_path_contains_ears_and_bounds(self) -> None:
        rect = QRectF(0.0, 0.0, 220.0, 34.0)
        path = build_desknotch_path(rect, bottom_radius=14.0, ear_radius=8.0)
        self.assertFalse(path.isEmpty())
        bounds = path.boundingRect()
        self.assertAlmostEqual(bounds.left(), 0.0, delta=0.5)
        self.assertAlmostEqual(bounds.right(), 220.0, delta=0.5)
        self.assertAlmostEqual(bounds.top(), 0.0, delta=0.5)
        self.assertAlmostEqual(bounds.bottom(), 34.0, delta=0.5)

    def test_create_rounded_pixmap_outputs_exact_square(self) -> None:
        src = QPixmap(120, 80)
        src.fill(QColor("#1DB954"))
        rounded = create_rounded_pixmap(src, 92, radius=12.0)
        self.assertEqual(rounded.width(), 92)
        self.assertEqual(rounded.height(), 92)
        self.assertFalse(rounded.isNull())

    def test_pin_button_prevents_auto_collapse_on_leave(self) -> None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        tmp.close()
        try:
            qs = QSettings(tmp.name, QSettings.Format.IniFormat)
            settings = SettingsManager(qsettings=qs)
            win = MainWindow(settings_manager=settings)
            win.set_state(DynamicIslandState.EXPANDED, animate=False)

            # Pin notch open
            win.btn_pin.setChecked(True)
            self.assertTrue(win._is_pinned)

            win.leaveEvent(QEvent(QEvent.Type.Leave))
            self.assertFalse(win._collapse_timer.isActive())

            # Unpin -> leaveEvent starts collapse timer again
            win.btn_pin.setChecked(False)
            self.assertFalse(win._is_pinned)
            win.leaveEvent(QEvent(QEvent.Type.Leave))
            self.assertTrue(win._collapse_timer.isActive())
        finally:
            if os.path.exists(tmp.name):
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass

    def test_settings_button_emits_signal(self) -> None:
        win = MainWindow()
        called = []
        win.open_settings_requested.connect(lambda: called.append(True))
        win.btn_settings.click()
        self.assertEqual(called, [True])

    def test_play_button_solid_white_style_and_source_header(self) -> None:
        win = MainWindow()
        self.assertIn("#FFFFFF", win.btn_play_pause.styleSheet())

        art = self._png_bytes(QColor(220, 50, 90))
        track = TrackInfo(
            title="Midnight City",
            artist="M83",
            album="Hurry Up",
            album_art_bytes=art,
            app_id="Spotify.exe",
            duration_ms=240000,
            position_ms=10000,
        )
        win.on_track_changed(track)
        win.on_status_changed(PlaybackStatus.PLAYING)
        self.assertEqual(win.lbl_source.text(), "SPOTIFY")

        win.on_status_changed(PlaybackStatus.PAUSED)
        self.assertEqual(win.lbl_source.text(), "PAUSED · SPOTIFY")

    def test_collapsed_notch_clock_thumb_and_pulse(self) -> None:
        notch = CollapsedNotchWidget()
        self.assertIn(":", notch.clock_label.text())

        art = self._png_bytes(QColor(40, 180, 90))
        notch.set_album_thumbnail(art)
        self.assertTrue(notch._has_album_thumb)
        self.assertEqual(notch.icon_label.pixmap().width(), 18)

        notch.set_playback_status(PlaybackStatus.PLAYING)
        notch.set_bar_heights([0.4, 0.8, 0.6, 0.3, 0.2])
        self.assertTrue(notch.pulse_bars.is_animated)

    def test_playing_status_shows_notch_from_hidden_when_not_manually_hidden(self) -> None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        tmp.close()
        try:
            qs = QSettings(tmp.name, QSettings.Format.IniFormat)
            settings = SettingsManager(qsettings=qs)
            win = MainWindow(settings_manager=settings)
            self.assertEqual(win.island_state, DynamicIslandState.HIDDEN)

            # Media begins playing -> pops notch open automatically unless manually hidden
            win.on_status_changed(PlaybackStatus.PLAYING)
            self.assertEqual(win.island_state, DynamicIslandState.COLLAPSED)
            self.assertTrue(win.isVisible())
        finally:
            if os.path.exists(tmp.name):
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
