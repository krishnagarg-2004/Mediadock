"""Main application widget window for MediaDock."""

import time
from typing import Any, Optional
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QAbstractAnimation, QRect, QEasingCurve
from PySide6.QtGui import QKeyEvent, QColor, QFont, QPixmap, QPainter, QCloseEvent, QIcon, QPen, QPainterPath, QAction, QGuiApplication

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QGraphicsOpacityEffect,
    QMenu,
)


from enum import Enum, auto


class DynamicIslandState(Enum):
    """Authoritative presentation states for the Dynamic Island."""
    HIDDEN = auto()
    COLLAPSED = auto()
    EXPANDED = auto()


from src.core.models import TrackInfo, PlaybackStatus, VolumeState
from src.core.media_core import MediaCore
from src.core.settings import SettingsManager
from src.ui.frameless_window import FramelessWindow
from src.ui.components import ElidedLabel
from src.ui.components_island import ReactiveVisualizerWidget, CollapsedCapsuleWidget, CollapsedNotchWidget
from src.ui.theme import (
    COLOR_BG_ISLAND,
    COLOR_ACCENT_BLUE,
    extract_dominant_color,
    get_button_stylesheet,
    get_slider_stylesheet,
    get_status_badge_style,
    get_svg_icon,
)


def create_volume_icon_pixmap(muted: bool, size: int = 16, color: QColor = QColor("#CDD6F4")) -> QPixmap:
    """Generate HiDPI vector QPixmap for speaker mute/unmute icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    # Draw speaker body
    body_path = QPainterPath()
    body_path.moveTo(2, 5)
    body_path.lineTo(5, 5)
    body_path.lineTo(8, 2)
    body_path.lineTo(8, 12)
    body_path.lineTo(5, 9)
    body_path.lineTo(2, 9)
    body_path.closeSubpath()

    painter.fillPath(body_path, color)
    painter.drawPath(body_path)

    if muted:
        # Draw X cross line
        painter.drawLine(10, 4, 14, 10)
        painter.drawLine(14, 4, 10, 10)
    else:
        # Draw sound wave arc
        painter.drawArc(8, 4, 5, 6, -60 * 16, 120 * 16)

    painter.end()
    return pixmap


def _format_time_ms(ms: int) -> str:
    """Format milliseconds into MM:SS string, clamping negative values to 00:00."""
    if ms <= 0:
        return "00:00"
    total_seconds = int(ms // 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


TOP_OFFSET_PX: int = 0
COLLAPSED_SIZE = (180, 40)
EXPANDED_SIZE = (360, 160)


class MainWindow(FramelessWindow):
    """Main application widget window for MediaDock with interactive controls and progress tracking."""

    def __init__(
        self,
        media_core: Optional[MediaCore] = None,
        settings_manager: Optional[SettingsManager] = None,
        parent: Optional[QWidget] = None,
        border_radius: float = 16.0,
        bg_color: QColor = COLOR_BG_ISLAND,
    ) -> None:
        super().__init__(parent, border_radius=border_radius, bg_color=bg_color, allow_drag=False)
        self.setWindowTitle("MediaDock")

        self._media_core = media_core
        self._settings_manager = settings_manager or SettingsManager()
        self._default_art_pixmap = self._create_default_art_pixmap()

        # Dynamic Island State Machine & Collapse Timer Initialization
        self._state: DynamicIslandState = DynamicIslandState.HIDDEN
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(self._settings_manager.get_collapse_delay_ms())
        self._collapse_timer.timeout.connect(self._on_collapse_timer_timeout)

        # Dynamic Island Geometry Animation (180 ms OutCubic pop-in / pop-out)
        self._geom_anim = QPropertyAnimation(self, b"geometry", self)
        self._geom_anim.setDuration(180)
        self._geom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._geom_anim.finished.connect(self._on_geom_anim_finished)

        # State tracking for UI clock interpolation & seeking state machine
        self._duration_ms: int = 0
        self._last_position_ms: int = 0
        self._last_position_update_time: float = 0.0
        self._is_seeking: bool = False
        self._is_setting_volume: bool = False
        self._is_compact_mode: bool = False
        self._is_quitting: bool = False
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

        # Apply settings configuration & enforce initial state
        self._apply_always_on_top(self._settings_manager.get_always_on_top())
        self._settings_manager.settings_changed.connect(self._on_setting_changed)

        # Listen for primary screen geometry changes
        primary_screen = QGuiApplication.primaryScreen()
        if primary_screen:
            primary_screen.geometryChanged.connect(lambda _: self.update_top_center_position())

        # Setup UI position interpolation QTimer (250 ms)
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(250)
        self._position_timer.timeout.connect(self._on_position_timer_tick)

        if self._media_core:
            self._connect_media_core()

        # Initial State Calculation
        if not self._settings_manager.get_dynamic_island_enabled():
            self.set_state(DynamicIslandState.HIDDEN, animate=False)
        elif self._media_core and self._media_core.is_session_available():
            self.set_state(DynamicIslandState.COLLAPSED, animate=False)
        else:
            self.set_state(DynamicIslandState.HIDDEN, animate=False)

    @property
    def island_state(self) -> DynamicIslandState:
        """Return current authoritative DynamicIslandState."""
        return self._state

    @property
    def notch_widget(self) -> CollapsedNotchWidget:
        """Return reference to the collapsed notch presentation widget."""
        return self._capsule_widget

    def _on_geom_anim_finished(self) -> None:
        """Lock fixed size for target state upon pop-in / pop-out animation completion."""
        if self._state == DynamicIslandState.COLLAPSED:
            target_rect = self.compute_top_center_collapsed_geometry()
            self.setGeometry(target_rect)
            self._capsule_widget.setFixedSize(COLLAPSED_SIZE[0], COLLAPSED_SIZE[1])
            self.setFixedSize(COLLAPSED_SIZE[0], COLLAPSED_SIZE[1])
        elif self._state == DynamicIslandState.EXPANDED:
            target_rect = self.compute_top_center_expanded_geometry()
            self.setGeometry(target_rect)
            self._expanded_widget.setFixedSize(EXPANDED_SIZE[0], EXPANDED_SIZE[1])
            self.setFixedSize(EXPANDED_SIZE[0], EXPANDED_SIZE[1])

    def set_state(self, state: DynamicIslandState, animate: bool = True) -> None:
        """Transition Dynamic Island to new state (HIDDEN, COLLAPSED, or EXPANDED) with optional pop-in/pop-out animation."""
        if not self._settings_manager.get_dynamic_island_enabled():
            state = DynamicIslandState.HIDDEN

        old_state = self._state
        self._state = state

        if state == DynamicIslandState.HIDDEN:
            if self._collapse_timer.isActive():
                self._collapse_timer.stop()
            if self._geom_anim.state() == QAbstractAnimation.State.Running:
                self._geom_anim.stop()
            self._capsule_widget.hide()
            self._expanded_widget.hide()
            self.hide()

        elif state == DynamicIslandState.COLLAPSED:
            if self._collapse_timer.isActive():
                self._collapse_timer.stop()

            target_rect = self.compute_top_center_collapsed_geometry()

            if animate and old_state == DynamicIslandState.EXPANDED and self.isVisible():
                if self._geom_anim.state() == QAbstractAnimation.State.Running:
                    self._geom_anim.stop()

                start_rect = self.geometry()

                self.setMinimumSize(0, 0)
                self.setMaximumSize(16777215, 16777215)
                self._expanded_widget.setMinimumSize(0, 0)
                self._expanded_widget.setMaximumSize(16777215, 16777215)
                self._capsule_widget.setMinimumSize(0, 0)
                self._capsule_widget.setMaximumSize(16777215, 16777215)

                self._expanded_widget.hide()
                self._capsule_widget.show()

                self._geom_anim.setStartValue(start_rect)
                self._geom_anim.setEndValue(target_rect)
                self._geom_anim.start()
            else:
                if self._geom_anim.state() == QAbstractAnimation.State.Running:
                    self._geom_anim.stop()
                self._expanded_widget.hide()
                self._capsule_widget.show()
                self._capsule_widget.setFixedSize(COLLAPSED_SIZE[0], COLLAPSED_SIZE[1])
                self.setFixedSize(COLLAPSED_SIZE[0], COLLAPSED_SIZE[1])
                self.setGeometry(target_rect)
                self.show()

        elif state == DynamicIslandState.EXPANDED:
            if self._collapse_timer.isActive():
                self._collapse_timer.stop()

            target_rect = self.compute_top_center_expanded_geometry()

            if animate and old_state == DynamicIslandState.COLLAPSED and self.isVisible():
                if self._geom_anim.state() == QAbstractAnimation.State.Running:
                    self._geom_anim.stop()

                start_rect = self.geometry()

                self.setMinimumSize(0, 0)
                self.setMaximumSize(16777215, 16777215)
                self._expanded_widget.setMinimumSize(0, 0)
                self._expanded_widget.setMaximumSize(16777215, 16777215)
                self._capsule_widget.setMinimumSize(0, 0)
                self._capsule_widget.setMaximumSize(16777215, 16777215)

                self._capsule_widget.hide()
                self._expanded_widget.show()

                self._geom_anim.setStartValue(start_rect)
                self._geom_anim.setEndValue(target_rect)
                self._geom_anim.start()
            else:
                if self._geom_anim.state() == QAbstractAnimation.State.Running:
                    self._geom_anim.stop()
                self._capsule_widget.hide()
                self._expanded_widget.show()
                self._expanded_widget.setFixedSize(EXPANDED_SIZE[0], EXPANDED_SIZE[1])
                self.setFixedSize(EXPANDED_SIZE[0], EXPANDED_SIZE[1])
                self.setGeometry(target_rect)
                self.show()

    def toggle_dynamic_island_visibility(self) -> None:
        """Toggle Dynamic Island between HIDDEN and COLLAPSED/EXPANDED."""
        if self._state == DynamicIslandState.HIDDEN:
            if self._settings_manager.get_dynamic_island_enabled():
                self.set_state(DynamicIslandState.COLLAPSED)
        else:
            self.set_state(DynamicIslandState.HIDDEN)

    def enterEvent(self, event) -> None:
        """Handle mouse enter event on Dynamic Island."""
        try:
            super().enterEvent(event)
        except Exception:
            pass
        if self._state == DynamicIslandState.COLLAPSED:
            if self._collapse_timer.isActive():
                self._collapse_timer.stop()
            self.set_state(DynamicIslandState.EXPANDED)
        elif self._state == DynamicIslandState.EXPANDED:
            if self._collapse_timer.isActive():
                self._collapse_timer.stop()

    def leaveEvent(self, event) -> None:
        """Handle mouse leave event on Dynamic Island."""
        super().leaveEvent(event)
        if self._state == DynamicIslandState.EXPANDED:
            delay_ms = self._settings_manager.get_collapse_delay_ms()
            self._collapse_timer.start(delay_ms)

    def _on_collapse_timer_timeout(self) -> None:
        """Single-shot collapse timer timeout handler."""
        if self._state == DynamicIslandState.EXPANDED:
            self.set_state(DynamicIslandState.COLLAPSED)

    def compute_top_center_geometry(self, width: int, height: int) -> QRect:
        """Calculate top-center QRect on primary screen work area with TOP_OFFSET_PX margin."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return QRect(0, 0, width, height)
        geom = screen.availableGeometry()
        x = geom.left() + (geom.width() - width) // 2
        y = geom.top() + TOP_OFFSET_PX
        return QRect(x, y, width, height)

    def compute_top_center_collapsed_geometry(self) -> QRect:
        """Calculate target top-center QRect for COLLAPSED state (180x40 px)."""
        return self.compute_top_center_geometry(COLLAPSED_SIZE[0], COLLAPSED_SIZE[1])

    def compute_top_center_expanded_geometry(self) -> QRect:
        """Calculate target top-center QRect for EXPANDED state (360x160 px)."""
        return self.compute_top_center_geometry(EXPANDED_SIZE[0], EXPANDED_SIZE[1])

    def update_top_center_position(self, width: Optional[int] = None, height: Optional[int] = None) -> None:
        """Reposition and resize window to top-center of primary screen work area."""
        if width is not None and height is not None:
            w, h = width, height
        elif self._state == DynamicIslandState.EXPANDED:
            w, h = EXPANDED_SIZE
        else:
            w, h = COLLAPSED_SIZE
        target_rect = self.compute_top_center_geometry(w, h)
        self.setGeometry(target_rect)

    def showEvent(self, event) -> None:
        """Ensure top-center position is updated upon window show event."""
        super().showEvent(event)
        self.update_top_center_position()

    @property
    def is_compact_mode(self) -> bool:
        """Deprecated compatibility property. Return True if Dynamic Island is in COLLAPSED state."""
        return self._state == DynamicIslandState.COLLAPSED

    def set_compact_mode(self, enabled: bool) -> None:
        """Deprecated compatibility wrapper. Map enabled=True to COLLAPSED state and False to EXPANDED state."""
        self._is_compact_mode = enabled
        if self._settings_manager and self._settings_manager.get_compact_mode() != enabled:
            self._settings_manager.set_compact_mode(enabled)

        if enabled:
            self.set_state(DynamicIslandState.COLLAPSED)
        else:
            self.set_state(DynamicIslandState.EXPANDED)


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

    def _apply_always_on_top(self, on_top: bool) -> None:
        """Apply or remove WindowStaysOnTopHint window flag."""
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
        if self.isVisible():
            self.show()

    def force_close(self) -> None:
        """Flag window as quitting so closeEvent accepts closing instead of hiding to tray."""
        self._is_quitting = True
        self.close()

    def _restore_position(self) -> None:
        """Restore window top-center position on primary screen."""
        self.update_top_center_position()

    def _save_position(self) -> None:
        """Save current window position (no-op for top-center Dynamic Island)."""
        pass

    def _on_setting_changed(self, key: str, value: Any) -> None:
        """Handle settings_changed signal from SettingsManager."""
        if key == "window/always_on_top":
            self._apply_always_on_top(bool(value))
        elif key == "dynamic_island/enabled":
            if not bool(value):
                self.set_state(DynamicIslandState.HIDDEN)
            elif self._media_core and self._media_core.is_session_available():
                self.set_state(DynamicIslandState.COLLAPSED)
        elif key == "dynamic_island/collapse_delay_ms":
            self._collapse_timer.setInterval(int(value))
        elif key == "window/compact_mode":
            if bool(value) != self._is_compact_mode:
                self.set_compact_mode(bool(value))

    def _init_ui(self) -> None:
        """Initialize the widget layout, collapsed capsule container, and expanded card container."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # 1. Collapsed Notch Component Container
        self._capsule_widget = CollapsedNotchWidget(self)
        self._notch_widget = self._capsule_widget
        root_layout.addWidget(self._capsule_widget)

        # 2. Expanded Card Container Widget
        self._expanded_widget = QWidget(self)
        expanded_layout = QVBoxLayout(self._expanded_widget)
        expanded_layout.setContentsMargins(15, 12, 15, 12)
        expanded_layout.setSpacing(8)

        # Top section: Album Art + Meta & Transport Controls
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        # Left Column: Album Art Thumbnail
        self.art_label = QLabel(self._expanded_widget)
        self.art_label.setFixedSize(72, 72)
        self.art_label.setPixmap(self._default_art_pixmap)
        self.art_label.setScaledContents(True)
        self.art_label.setStyleSheet("border-radius: 8px; background-color: #313244;")

        # Right Column: Track Info & Transport Buttons
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = ElidedLabel("MediaDock", self._expanded_widget)
        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #FFFFFF;")

        self.artist_label = ElidedLabel("No Media Playing", self._expanded_widget)
        sub_font = QFont("Segoe UI", 9)
        self.artist_label.setFont(sub_font)
        self.artist_label.setStyleSheet("color: #A6ADC8;")

        self.status_label = QLabel("CLOSED", self._expanded_widget)
        status_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        self.status_label.setFont(status_font)
        text, text_hex, bg_hex = get_status_badge_style(PlaybackStatus.CLOSED)
        self.status_label.setStyleSheet(
            f"color: {text_hex}; background-color: {bg_hex}; border-radius: 4px; padding: 2px 6px;"
        )

        # Reactive Visualizer
        self._visualizer = ReactiveVisualizerWidget(bar_count=5, parent=self._expanded_widget)

        # Transport Controls Row
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 2, 0, 0)
        controls_layout.setSpacing(8)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        btn_style = get_button_stylesheet()

        self.btn_prev = QPushButton(self._expanded_widget)
        self.btn_prev.setFixedSize(30, 24)
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.setIcon(get_svg_icon("previous", 14, QColor("#CDD6F4")))
        self.btn_prev.clicked.connect(self._on_btn_prev_clicked)

        self.btn_play_pause = QPushButton(self._expanded_widget)
        self.btn_play_pause.setFixedSize(36, 24)
        self.btn_play_pause.setStyleSheet(btn_style)
        self.btn_play_pause.setIcon(get_svg_icon("play", 14, QColor("#CDD6F4")))
        self.btn_play_pause.clicked.connect(self._on_btn_play_pause_clicked)

        self.btn_next = QPushButton(self._expanded_widget)
        self.btn_next.setFixedSize(30, 24)
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.setIcon(get_svg_icon("next", 14, QColor("#CDD6F4")))
        self.btn_next.clicked.connect(self._on_btn_next_clicked)

        # Master Volume & Mute Controls
        self.btn_mute = QPushButton(self._expanded_widget)
        self.btn_mute.setFixedSize(26, 24)
        self.btn_mute.setStyleSheet(btn_style)
        self.btn_mute.setIcon(get_svg_icon("volume", 14, QColor("#CDD6F4")))
        self.btn_mute.clicked.connect(self._on_btn_mute_clicked)

        self.slider_volume = QSlider(Qt.Orientation.Horizontal, self._expanded_widget)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100)
        self.slider_volume.setFixedWidth(56)
        self.slider_volume.setStyleSheet(get_slider_stylesheet(self._current_accent))
        self.slider_volume.valueChanged.connect(self._on_volume_slider_changed)

        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.btn_play_pause)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addWidget(self.btn_mute)
        controls_layout.addWidget(self.slider_volume)
        controls_layout.addWidget(self._visualizer)
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

        self.lbl_position = QLabel("00:00", self._expanded_widget)
        self.lbl_position.setFont(time_font)
        self.lbl_position.setStyleSheet("color: #A6ADC8;")

        self.lbl_duration = QLabel("00:00", self._expanded_widget)
        self.lbl_duration.setFont(time_font)
        self.lbl_duration.setStyleSheet("color: #A6ADC8;")

        self.progress_slider = QSlider(Qt.Orientation.Horizontal, self._expanded_widget)
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

        expanded_layout.addLayout(top_layout)
        expanded_layout.addLayout(progress_layout)

        root_layout.addWidget(self._expanded_widget)

    def _connect_media_core(self) -> None:
        """Connect MediaCore signals to MainWindow slots and initialize display."""
        if not self._media_core:
            return

        self._media_core.track_changed.connect(self.on_track_changed)
        self._media_core.playback_status_changed.connect(self.on_status_changed)
        self._media_core.session_availability_changed.connect(
            self.on_session_availability_changed
        )
        self._media_core.volume_changed.connect(self.on_volume_changed)
        if hasattr(self._media_core, "audio_visualizer_updated"):
            self._media_core.audio_visualizer_updated.connect(
                self.on_audio_visualizer_updated
            )

        # Initial display sync
        self.on_track_changed(self._media_core.get_current_track())
        self.on_status_changed(self._media_core.get_playback_status())
        self.on_session_availability_changed(self._media_core.is_session_available())
        self.on_volume_changed(self._media_core.get_volume_state())


    # --- Button & Slider Click Handlers ---

    def _on_btn_prev_clicked(self) -> None:
        if self._media_core:
            self._media_core.previous_track()

    def _on_btn_play_pause_clicked(self) -> None:
        if self._media_core:
            self._media_core.toggle_play_pause()

    def _on_btn_next_clicked(self) -> None:
        if self._media_core:
            self._media_core.next_track()

    def _on_btn_mute_clicked(self) -> None:
        if self._media_core:
            self._media_core.toggle_mute()

    def _on_volume_slider_changed(self, value: int) -> None:
        if self._is_setting_volume:
            return
        self._is_setting_volume = True
        try:
            if self._media_core:
                self._media_core.set_volume(value)
        finally:
            self._is_setting_volume = False

    def on_volume_changed(self, state: VolumeState) -> None:
        """Slot for volume_changed signal. Updates slider and mute icon or hides if unsupported."""
        if not state.is_supported:
            self.btn_mute.hide()
            self.slider_volume.hide()
            return

        self.btn_mute.show()
        self.slider_volume.show()

        if not self._is_setting_volume:
            self._is_setting_volume = True
            try:
                self.slider_volume.setValue(state.volume_percent)
            finally:
                self._is_setting_volume = False

        icon_color = QColor("#A6ADC8") if state.is_muted else QColor("#CDD6F4")
        icon_name = "mute" if state.is_muted or state.volume_percent == 0 else "volume"
        self.btn_mute.setIcon(get_svg_icon(icon_name, 14, icon_color))


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
        """Slot for track_changed signal. Updates capsule and expanded track labels."""
        source_name = ""
        if self._media_core and hasattr(self._media_core, "get_active_session_info"):
            try:
                sess = self._media_core.get_active_session_info()
                if sess:
                    source_name = getattr(sess, "display_name", "") or getattr(sess, "app_id", "") or ""
            except Exception:
                pass
        if not source_name and track and hasattr(track, "app_id") and track.app_id:
            source_name = track.app_id

        self._capsule_widget.set_source_info(source_name, str(track.title), str(track.artist))

        # Update expanded card metadata
        self.title_label.setText(track.title)
        self.artist_label.setText(track.artist)
        self._update_album_art(track.album_art_bytes)

        # Dynamic album art accent extraction & styling
        self._current_accent = extract_dominant_color(track.album_art_bytes)
        self.progress_slider.setStyleSheet(get_slider_stylesheet(self._current_accent))
        self._capsule_widget.set_accent_color(self._current_accent)
        self._visualizer.set_bar_color(self._current_accent)

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

    def on_audio_visualizer_updated(self, bars: list) -> None:
        """Slot for audio_visualizer_updated signal. Updates visualizer bar heights during active playback."""
        if self._current_status == PlaybackStatus.PLAYING:
            self._visualizer.set_bar_heights(bars)

    def on_status_changed(self, status: PlaybackStatus) -> None:
        """Slot for playback_status_changed signal. Updates badge, capsule, and visualizer."""
        self._current_status = status

        self._capsule_widget.set_playback_status(status)
        self._visualizer.set_playback_status(status)

        text, text_hex, bg_hex = get_status_badge_style(status)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {text_hex}; background-color: {bg_hex}; border-radius: 4px; padding: 2px 6px;"
        )

        if status == PlaybackStatus.PLAYING:
            self.btn_play_pause.setIcon(get_svg_icon("pause", 14, QColor("#CDD6F4")))
            if self._duration_ms > 0 and not self._position_timer.isActive():
                self._position_timer.start()
        elif status in (PlaybackStatus.PAUSED, PlaybackStatus.STOPPED, PlaybackStatus.CLOSED):
            self.btn_play_pause.setIcon(get_svg_icon("play", 14, QColor("#CDD6F4")))
            if self._position_timer.isActive():
                self._position_timer.stop()
            self._visualizer.clear_bar_heights()

    def on_session_availability_changed(self, available: bool) -> None:
        """Slot for session_availability_changed signal. Updates control state & Dynamic Island visibility."""
        self.btn_prev.setEnabled(available)
        self.btn_play_pause.setEnabled(available)
        self.btn_next.setEnabled(available)
        self.progress_slider.setEnabled(available)

        if available:
            if self._settings_manager.get_dynamic_island_enabled():
                if self._state == DynamicIslandState.HIDDEN:
                    self.set_state(DynamicIslandState.COLLAPSED)
        else:
            if self._position_timer.isActive():
                self._position_timer.stop()
            self.on_track_changed(TrackInfo.empty())
            self.on_status_changed(PlaybackStatus.CLOSED)
            # Session closed -> transition to HIDDEN while process remains alive
            self.set_state(DynamicIslandState.HIDDEN)

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

    # --- Event Filters & Lifecycle ---

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events. Closes (or hides) window on Escape key press."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event based on close_to_tray preference and quit state."""
        if self._fade_anim.state() == QAbstractAnimation.State.Running:
            self._fade_anim.stop()
        self._opacity_effect.setOpacity(1.0)

        if self._position_timer.isActive():
            self._position_timer.stop()
        if self._collapse_timer.isActive():
            self._collapse_timer.stop()

        self._save_position()

        # If app is explicitly quitting, accept close event
        if self._is_quitting:
            event.accept()
        elif self._settings_manager and self._settings_manager.get_close_to_tray():
            event.ignore()
            self.set_state(DynamicIslandState.HIDDEN)
        else:
            event.accept()
            QApplication.quit()

    def contextMenuEvent(self, event) -> None:
        """Show context menu on right click."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #1E1E2E; color: #CDD6F4; border: 1px solid #45475A; border-radius: 6px; padding: 4px; }\n"
            "QMenu::item:selected { background-color: #313244; border-radius: 4px; }"
        )
        toggle_action = QAction("Toggle Dynamic Island", self)
        toggle_action.triggered.connect(self.toggle_dynamic_island_visibility)
        menu.addAction(toggle_action)
        menu.exec(event.globalPos())
