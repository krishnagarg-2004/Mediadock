"""Main application widget window for MediaDock."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QColor, QFont, QPixmap, QPainter, QCloseEvent
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel

from src.core.models import TrackInfo, PlaybackStatus
from src.core.media_core import MediaCore
from src.ui.frameless_window import FramelessWindow


class MainWindow(FramelessWindow):
    """Main floating widget window for MediaDock."""

    def __init__(
        self,
        media_core: Optional[MediaCore] = None,
        parent: Optional[QWidget] = None,
        border_radius: float = 16.0,
        bg_color: QColor = QColor("#1E1E2E"),
    ) -> None:
        super().__init__(parent, border_radius=border_radius, bg_color=bg_color)
        self.setWindowTitle("MediaDock")
        self.resize(340, 120)

        self._media_core = media_core
        self._default_art_pixmap = self._create_default_art_pixmap()

        self._init_ui()

        if self._media_core:
            self._connect_media_core()

    def _create_default_art_pixmap(self) -> QPixmap:
        """Generate a clean 80x80 default placeholder pixmap for missing artwork."""
        pixmap = QPixmap(80, 80)
        pixmap.fill(QColor("#313244"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#CDD6F4"))
        font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "♪")
        painter.end()
        return pixmap

    def _init_ui(self) -> None:
        """Initialize the horizontal widget layout and placeholder contents."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Left Column: Album Art Thumbnail
        self.art_label = QLabel(self)
        self.art_label.setFixedSize(80, 80)
        self.art_label.setPixmap(self._default_art_pixmap)
        self.art_label.setScaledContents(True)
        self.art_label.setStyleSheet("border-radius: 8px; background-color: #313244;")

        # Right Column: Track Info & Status
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel("MediaDock", self)
        title_font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #FFFFFF;")
        self.title_label.setWordWrap(False)

        self.artist_label = QLabel("No Media Playing", self)
        sub_font = QFont("Segoe UI", 9)
        self.artist_label.setFont(sub_font)
        self.artist_label.setStyleSheet("color: #A6ADC8;")
        self.artist_label.setWordWrap(False)

        self.status_label = QLabel("CLOSED", self)
        status_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #6C7086;")

        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        info_layout.addWidget(self.status_label)

        main_layout.addWidget(self.art_label)
        main_layout.addLayout(info_layout)

    def _connect_media_core(self) -> None:
        """Connect MediaCore signals to MainWindow slots and initialize display."""
        if not self._media_core:
            return

        self._media_core.track_changed.connect(self.on_track_changed)
        self._media_core.playback_status_changed.connect(self.on_status_changed)
        self._media_core.session_availability_changed.connect(
            self.on_session_availability_changed
        )

        # Initial display sync
        self.on_track_changed(self._media_core.get_current_track())
        self.on_status_changed(self._media_core.get_playback_status())
        self.on_session_availability_changed(self._media_core.is_session_available())

    # --- Qt Signal Slots ---

    def on_track_changed(self, track: TrackInfo) -> None:
        """Slot for track_changed signal. Updates title, artist, and album art."""
        self.title_label.setText(track.title)
        self.artist_label.setText(track.artist)
        self._update_album_art(track.album_art_bytes)

    def on_status_changed(self, status: PlaybackStatus) -> None:
        """Slot for playback_status_changed signal. Updates status badge."""
        self.status_label.setText(status.value)
        if status == PlaybackStatus.PLAYING:
            self.status_label.setStyleSheet("color: #A6E3A1;")  # Green
        elif status == PlaybackStatus.PAUSED:
            self.status_label.setStyleSheet("color: #F9E2AF;")  # Yellow
        elif status == PlaybackStatus.STOPPED:
            self.status_label.setStyleSheet("color: #F38BA8;")  # Red
        else:
            self.status_label.setStyleSheet("color: #6C7086;")  # Muted Gray

    def on_session_availability_changed(self, available: bool) -> None:
        """Slot for session_availability_changed signal. Handles no-session fallback."""
        if not available:
            self.on_track_changed(TrackInfo.empty())
            self.on_status_changed(PlaybackStatus.CLOSED)

    def _update_album_art(self, art_bytes: Optional[bytes]) -> None:
        """Load raw image bytes into QPixmap in memory without disk files."""
        if art_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(art_bytes):
                scaled = pixmap.scaled(
                    80,
                    80,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.art_label.setPixmap(scaled)
                return
        self.art_label.setPixmap(self._default_art_pixmap)

    # --- Event Filters ---

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Close window on Escape key press."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up MediaCore upon window close."""
        if self._media_core:
            self._media_core.stop()
        super().closeEvent(event)
