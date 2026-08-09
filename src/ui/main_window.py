"""Main application widget window for MediaDock."""

import time
from typing import Optional
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QAbstractAnimation
from PySide6.QtGui import QKeyEvent, QColor, QFont, QPixmap, QPainter, QCloseEvent
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QGraphicsOpacityEffect,
)

from src.core.models import TrackInfo, PlaybackStatus
from src.core.media_core import MediaCore
from src.ui.frameless_window import FramelessWindow
from src.ui.components import ElidedLabel
from src.ui.theme import (
    COLOR_ACCENT_BLUE,
    extract_dominant_color,
    get_button_stylesheet,
    get_slider_stylesheet,
    get_status_badge_style,
)


def _format_time_ms(ms: int) -> str:
    """Format milliseconds into MM:SS string, clamping negative values to 00:00."""
    if ms <= 0:
        return "00:00"
    total_seconds = int(ms // 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


class MainWindow(FramelessWindow):
    """Main floating widget window for MediaDock with interactive controls and progress tracking."""

    def __init__(
        self,
        media_core: Optional[MediaCore] = None,
        parent: Optional[QWidget] = None,
        border_radius: float = 16.0,
        bg_color: QColor = QColor("#1E1E2E"),
    ) -> None:
        super().__init__(parent, border_radius=border_radius, bg_color=bg_color)
        self.setWindowTitle("MediaDock")
        self.resize(360, 140)

        self._media_core = media_core
        self._default_art_pixmap = self._create_default_art_pixmap()

        # State tracking for UI clock interpolation & seeking state machine
        self._duration_ms: int = 0
        self._last_position_ms: int = 0
        self._last_position_update_time: float = 0.0
        self._is_seeking: bool = False
        self._current_status: PlaybackStatus = PlaybackStatus.CLOSED
        self._current_accent: QColor = COLOR_ACCENT_BLUE

        # Setup subtle opacity fade animation effect for track changes
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(120)
        self._fade_anim.finished.connect(self._on_fade_anim_finished)

        self._init_ui()

        # Setup UI position interpolation QTimer (250 ms)
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(250)
        self._position_timer.timeout.connect(self._on_position_timer_tick)

        if self._media_core:
            self._connect_media_core()

    def _create_default_art_pixmap(self) -> QPixmap:
        """Generate a clean 72x72 default placeholder pixmap for missing artwork."""
        pixmap = QPixmap(72, 72)
        pixmap.fill(QColor("#313244"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#CDD6F4"))
        font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "♪")
        painter.end()
        return pixmap

    def _on_fade_anim_finished(self) -> None:
        """Ensure widget opacity is restored to 1.0 upon animation completion."""
        self._opacity_effect.setOpacity(1.0)

    def _trigger_track_fade_animation(self) -> None:
        """Trigger a subtle non-blocking opacity cross-fade on track changes, restoring opacity to 1.0."""
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            self._fade_anim.stop()
        self._opacity_effect.setOpacity(1.0)
        self._fade_anim.setStartValue(0.7)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()


    def _init_ui(self) -> None:
        """Initialize the widget layout, metadata labels, transport buttons, and progress slider."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(15, 12, 15, 12)
        root_layout.setSpacing(8)

        # Top section: Album Art + Meta & Transport Controls
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        # Left Column: Album Art Thumbnail
        self.art_label = QLabel(self)
        self.art_label.setFixedSize(72, 72)
        self.art_label.setPixmap(self._default_art_pixmap)
        self.art_label.setScaledContents(True)
        self.art_label.setStyleSheet("border-radius: 8px; background-color: #313244;")

        # Right Column: Track Info & Transport Buttons
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = ElidedLabel("MediaDock", self)
        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #FFFFFF;")

        self.artist_label = ElidedLabel("No Media Playing", self)
        sub_font = QFont("Segoe UI", 9)
        self.artist_label.setFont(sub_font)
        self.artist_label.setStyleSheet("color: #A6ADC8;")

        self.status_label = QLabel("CLOSED", self)
        status_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        self.status_label.setFont(status_font)
        text, text_hex, bg_hex = get_status_badge_style(PlaybackStatus.CLOSED)
        self.status_label.setStyleSheet(
            f"color: {text_hex}; background-color: {bg_hex}; border-radius: 4px; padding: 2px 6px;"
        )

        # Transport Controls Row
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 2, 0, 0)
        controls_layout.setSpacing(8)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        btn_style = get_button_stylesheet()

        self.btn_prev = QPushButton("⏮", self)
        self.btn_prev.setFixedSize(30, 24)
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(self._on_btn_prev_clicked)

        self.btn_play_pause = QPushButton("▶", self)
        self.btn_play_pause.setFixedSize(36, 24)
        self.btn_play_pause.setStyleSheet(btn_style)
        self.btn_play_pause.clicked.connect(self._on_btn_play_pause_clicked)

        self.btn_next = QPushButton("⏭", self)
        self.btn_next.setFixedSize(30, 24)
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(self._on_btn_next_clicked)

        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.btn_play_pause)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addWidget(self.status_label)

        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        info_layout.addLayout(controls_layout)

        top_layout.addWidget(self.art_label)
        top_layout.addLayout(info_layout)

        # Bottom section: Progress Bar & Position Labels
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        time_font = QFont("Segoe UI", 8)

        self.lbl_position = QLabel("00:00", self)
        self.lbl_position.setFont(time_font)
        self.lbl_position.setStyleSheet("color: #A6ADC8;")

        self.lbl_duration = QLabel("00:00", self)
        self.lbl_duration.setFont(time_font)
        self.lbl_duration.setStyleSheet("color: #A6ADC8;")

        self.progress_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.setValue(0)
        self.progress_slider.setStyleSheet(get_slider_stylesheet(self._current_accent))

        # Seeking State Machine Connections
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)

        progress_layout.addWidget(self.lbl_position)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.lbl_duration)

        root_layout.addLayout(top_layout)
        root_layout.addLayout(progress_layout)

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

    # --- Button Click Handlers ---

    def _on_btn_prev_clicked(self) -> None:
        if self._media_core:
            self._media_core.previous_track()

    def _on_btn_play_pause_clicked(self) -> None:
        if self._media_core:
            self._media_core.toggle_play_pause()

    def _on_btn_next_clicked(self) -> None:
        if self._media_core:
            self._media_core.next_track()

    # --- Seeking State Machine ---

    def _on_slider_pressed(self) -> None:
        """sliderPressed: Enter seeking mode. Suspend automatic slider updates."""
        self._is_seeking = True

    def _on_slider_moved(self, value: int) -> None:
        """sliderMoved: Update position label from slider value without sending seek commands."""
        self.lbl_position.setText(_format_time_ms(value))

    def _on_slider_released(self) -> None:
        """sliderReleased: Send single seek_to_position command and exit seeking mode."""
        target_ms = self.progress_slider.value()
        if self._media_core:
            self._media_core.seek_to_position(target_ms)
        self._last_position_ms = target_ms
        self._last_position_update_time = time.monotonic()
        self._is_seeking = False

    # --- UI Position Interpolation Tick ---

    def _on_position_timer_tick(self) -> None:
        """UI-side position interpolation running on 250ms QTimer when PLAYING."""
        if self._current_status != PlaybackStatus.PLAYING or self._duration_ms <= 0:
            return

        elapsed_ms = int((time.monotonic() - self._last_position_update_time) * 1000)
        current_pos_ms = min(self._duration_ms, max(0, self._last_position_ms + elapsed_ms))

        self.lbl_position.setText(_format_time_ms(current_pos_ms))

        if not self._is_seeking:
            self.progress_slider.setValue(current_pos_ms)

    # --- Qt Signal Slots ---

    def on_track_changed(self, track: TrackInfo) -> None:
        """Slot for track_changed signal. Updates title, artist, art, accent, and timeline."""
        self.title_label.setText(track.title)
        self.artist_label.setText(track.artist)
        self._update_album_art(track.album_art_bytes)

        # Dynamic album art accent extraction & progress slider tinting
        self._current_accent = extract_dominant_color(track.album_art_bytes)
        self.progress_slider.setStyleSheet(get_slider_stylesheet(self._current_accent))

        # Timeline state update
        self._duration_ms = max(0, track.duration_ms)
        self._last_position_ms = max(0, track.position_ms)
        self._last_position_update_time = time.monotonic()

        self.lbl_duration.setText(_format_time_ms(self._duration_ms))
        if self._duration_ms > 0:
            self.progress_slider.setMaximum(self._duration_ms)
        else:
            self.progress_slider.setMaximum(0)

        self.lbl_position.setText(_format_time_ms(self._last_position_ms))
        if not self._is_seeking:
            self.progress_slider.setValue(min(self._last_position_ms, self._duration_ms))

        # Trigger smooth opacity transition
        self._trigger_track_fade_animation()

    def on_status_changed(self, status: PlaybackStatus) -> None:
        """Slot for playback_status_changed signal. Updates status badge, play/pause button, and timer."""
        self._current_status = status

        text, text_hex, bg_hex = get_status_badge_style(status)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {text_hex}; background-color: {bg_hex}; border-radius: 4px; padding: 2px 6px;"
        )

        if status == PlaybackStatus.PLAYING:
            self.btn_play_pause.setText("⏸")
            if self._duration_ms > 0 and not self._position_timer.isActive():
                self._position_timer.start()
        elif status == PlaybackStatus.PAUSED:
            self.btn_play_pause.setText("▶")
            if self._position_timer.isActive():
                self._position_timer.stop()
        elif status == PlaybackStatus.STOPPED:
            self.btn_play_pause.setText("▶")
            if self._position_timer.isActive():
                self._position_timer.stop()
        else:
            self.btn_play_pause.setText("▶")
            if self._position_timer.isActive():
                self._position_timer.stop()

    def on_session_availability_changed(self, available: bool) -> None:
        """Slot for session_availability_changed signal. Enables/disables controls."""
        self.btn_prev.setEnabled(available)
        self.btn_play_pause.setEnabled(available)
        self.btn_next.setEnabled(available)
        self.progress_slider.setEnabled(available)

        if not available:
            if self._position_timer.isActive():
                self._position_timer.stop()
            self.on_track_changed(TrackInfo.empty())
            self.on_status_changed(PlaybackStatus.CLOSED)

    def _update_album_art(self, art_bytes: Optional[bytes]) -> None:
        """Load raw image bytes into QPixmap in memory without disk files."""
        if art_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(art_bytes):
                scaled = pixmap.scaled(
                    72,
                    72,
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
        """Clean up position timer, animation effects & MediaCore upon window close."""
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            self._fade_anim.stop()
        self._opacity_effect.setOpacity(1.0)

        if self._position_timer.isActive():
            self._position_timer.stop()
        if self._media_core:
            self._media_core.stop()
        super().closeEvent(event)
