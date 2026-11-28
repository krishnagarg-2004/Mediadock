"""Main application widget window for MediaDock."""

import sys
import time
from dataclasses import replace
from typing import Any, Optional
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QAbstractAnimation, QRect, QRectF, QEasingCurve, Signal
from PySide6.QtGui import (
    QKeyEvent,
    QColor,
    QFont,
    QPixmap,
    QPainter,
    QCloseEvent,
    QIcon,
    QPen,
    QPainterPath,
    QAction,
    QGuiApplication,
    QCursor,
    QWheelEvent,
)

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QComboBox,
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
from src.core.fullscreen_detector import is_foreground_fullscreen
from src.media.lyrics_provider import LyricsProvider
from src.ui.frameless_window import FramelessWindow, build_desknotch_path
from src.ui.components import ElidedLabel, InteractiveScrubSlider, VolumeWedgeWidget
from src.ui.components_island import (
    ReactiveVisualizerWidget,
    CollapsedCapsuleWidget,
    CollapsedNotchWidget,
    classify_media_source,
)
from src.ui.theme import (
    COLOR_BG_ISLAND,
    COLOR_ACCENT_BLUE,
    NotchAppearance,
    create_rounded_pixmap,
    extract_dominant_color,
    get_button_stylesheet,
    get_desknotch_icon_button_stylesheet,
    get_desknotch_play_button_stylesheet,
    get_slider_stylesheet,
    get_status_badge_style,
    get_svg_icon,
    invalidate_banner_cache,
    paint_notch_surface,
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


COLLAPSED_TOP_OFFSET_PX: int = 0
EXPANDED_TOP_OFFSET_PX: int = 12
TOP_OFFSET_PX: int = COLLAPSED_TOP_OFFSET_PX
COLLAPSED_SIZE = (220, 34)
EXPANDED_SIZE = (410, 178)
LYRICS_BAR_EXTRA_HEIGHT: int = 38


class MainWindow(FramelessWindow):
    """Main application widget window for MediaDock with flush top-notch collapsed bar and oval expanded card."""

    open_settings_requested = Signal()
    lyrics_loaded_signal = Signal(str, bool)

    def __init__(
        self,
        media_core: Optional[MediaCore] = None,
        settings_manager: Optional[SettingsManager] = None,
        parent: Optional[QWidget] = None,
        border_radius: float = 14.0,
        bg_color: QColor = COLOR_BG_ISLAND,
    ) -> None:
        super().__init__(parent, border_radius=border_radius, ear_radius=8.0, bg_color=bg_color, allow_drag=False)
        self.setWindowTitle("MediaDock")

        self._media_core = media_core
        self._settings_manager = settings_manager or SettingsManager()
        self._custom_bg_override: bool = bg_color != COLOR_BG_ISLAND
        self._border_color: QColor = QColor(self._settings_manager.get_notch_border_color())
        self._appearance: NotchAppearance = NotchAppearance.from_settings(self._settings_manager)
        self._default_art_pixmap = self._create_default_art_pixmap()
        self._is_pinned: bool = False
        self._manually_hidden: bool = False
        self._current_source_display: str = "MediaDock"
        self._last_lyric_track_sig: tuple[str, str] = ("", "")

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
        self._shuffle_active: Optional[bool] = None
        self._repeat_mode: int = 0

        # Hover Intent Timer for expansion trigger
        self._hover_intent_timer = QTimer(self)
        self._hover_intent_timer.setSingleShot(True)
        self._hover_intent_timer.setInterval(self._settings_manager.get_hover_intent_delay_ms())
        self._hover_intent_timer.timeout.connect(self._on_hover_intent_timeout)

        # Fullscreen Game & App Auto-Hide Timer
        self._suppressed_by_fullscreen: bool = False
        self._fullscreen_timer = QTimer(self)
        self._fullscreen_timer.setInterval(1000)
        self._fullscreen_timer.timeout.connect(self._on_fullscreen_timer_tick)
        self._fullscreen_timer.start()

        # Synchronized Lyrics Provider
        self.lyrics_loaded_signal.connect(self._on_lyrics_loaded)
        self._lyrics_provider = LyricsProvider(
            on_lyrics_loaded=lambda key, has_synced: self.lyrics_loaded_signal.emit(key, has_synced)
        )

        # Setup subtle opacity fade animation effect for track changes
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(120)
        self._fade_anim.finished.connect(self._on_fade_anim_finished)

        self._init_ui()

        # Apply settings configuration & enforce initial state
        self._apply_appearance_colors()
        self._apply_always_on_top(self._settings_manager.get_always_on_top())
        self._settings_manager.settings_changed.connect(self._on_setting_changed)

        # Setup dynamic screen hotplug & geometry listeners (multi-monitor plug/unplug & resolution change)
        self._setup_screen_listeners()

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
            self._border_radius = 14.0
            self._ear_radius = 8.0
            target_rect = self.compute_top_center_collapsed_geometry()
            self.setGeometry(target_rect)
            self._capsule_widget.setFixedSize(COLLAPSED_SIZE[0], COLLAPSED_SIZE[1])
            self.setFixedSize(COLLAPSED_SIZE[0], COLLAPSED_SIZE[1])
        elif self._state == DynamicIslandState.EXPANDED:
            self._border_radius = 32.0
            self._ear_radius = 0.0
            exp_w, exp_h = self._get_expanded_size()
            target_rect = self.compute_top_center_expanded_geometry()
            self.setGeometry(target_rect)
            self._expanded_widget.setFixedSize(exp_w, exp_h)
            self.setFixedSize(exp_w, exp_h)
        self._enforce_topmost_zorder()
        self.update()

    def set_state(self, state: DynamicIslandState, animate: bool = True) -> None:
        """Transition Dynamic Island to new state (HIDDEN, COLLAPSED, or EXPANDED) with optional pop-in/pop-out animation."""
        if not self._settings_manager.get_dynamic_island_enabled():
            state = DynamicIslandState.HIDDEN

        old_state = self._state
        self._state = state

        if state != DynamicIslandState.EXPANDED:
            if hasattr(self, "_lyrics_drawer") and self._lyrics_drawer and self._lyrics_drawer.isVisible():
                self._lyrics_drawer.hide_drawer()

        if state == DynamicIslandState.HIDDEN:
            if self._collapse_timer.isActive():
                self._collapse_timer.stop()
            if self._geom_anim.state() == QAbstractAnimation.State.Running:
                self._geom_anim.stop()
            self._capsule_widget.hide()
            self._expanded_widget.hide()
            self.hide()

        elif state == DynamicIslandState.COLLAPSED:
            self._border_radius = 14.0
            self._ear_radius = 8.0
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
                self._enforce_topmost_zorder()

        elif state == DynamicIslandState.EXPANDED:
            self._border_radius = 32.0
            self._ear_radius = 0.0
            if self._collapse_timer.isActive():
                self._collapse_timer.stop()

            # Ensure lyrics label is correctly staged for expanded card
            if self._settings_manager.get_lyrics_enabled() and self._lyrics_provider.has_synced_lyrics():
                elapsed_ms = int((time.monotonic() - self._last_position_update_time) * 1000) if self._current_status == PlaybackStatus.PLAYING else 0
                cur_pos = max(0, self._last_position_ms + elapsed_ms)
                if self._duration_ms > 0:
                    cur_pos = min(self._duration_ms, cur_pos)
                lyric = self._lyrics_provider.get_current_lyric(cur_pos)
                self.lyrics_label.setText(f"♪ {lyric}" if lyric else "♪  ♫  ♪")
                self.lyrics_label.show()
            else:
                self.lyrics_label.hide()

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
                exp_w, exp_h = self._get_expanded_size()
                self._capsule_widget.hide()
                self._expanded_widget.show()
                self._expanded_widget.setFixedSize(exp_w, exp_h)
                self.setFixedSize(exp_w, exp_h)
                self.setGeometry(target_rect)
                self.show()
                self._enforce_topmost_zorder()

    def _enforce_topmost_zorder(self) -> None:
        """Promote notch window above desktop & maximized windows without stealing focus."""
        if not self.isVisible():
            return
        self.raise_()
        if sys.platform == "win32" and self._settings_manager.get_always_on_top():
            try:
                import ctypes
                HWND_TOPMOST = -1
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_NOACTIVATE = 0x0010
                SWP_SHOWWINDOW = 0x0040
                ctypes.windll.user32.SetWindowPos(
                    int(self.winId()),
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
                )
            except Exception:
                pass

    def toggle_dynamic_island_visibility(self) -> None:
        """Toggle Dynamic Island between HIDDEN and COLLAPSED/EXPANDED."""
        if self._state == DynamicIslandState.HIDDEN:
            if self._settings_manager.get_dynamic_island_enabled():
                self._manually_hidden = False
                self.set_state(DynamicIslandState.COLLAPSED)
        else:
            self._manually_hidden = True
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
            trigger = self._settings_manager.get_expand_trigger()
            if trigger == "hover":
                delay = self._settings_manager.get_hover_intent_delay_ms()
                if delay > 0:
                    self._hover_intent_timer.start(delay)
                else:
                    self.set_state(DynamicIslandState.EXPANDED)
        elif self._state == DynamicIslandState.EXPANDED:
            if self._collapse_timer.isActive():
                self._collapse_timer.stop()

    def leaveEvent(self, event) -> None:
        """Handle mouse leave event on Dynamic Island."""
        super().leaveEvent(event)
        if self._hover_intent_timer.isActive():
            self._hover_intent_timer.stop()
        if self._state == DynamicIslandState.EXPANDED and not self._is_pinned:
            delay_ms = self._settings_manager.get_collapse_delay_ms()
            self._collapse_timer.start(delay_ms)

    def _on_hover_intent_timeout(self) -> None:
        """Hover intent timer timeout handler."""
        if self._state == DynamicIslandState.COLLAPSED and self.underMouse():
            self.set_state(DynamicIslandState.EXPANDED)

    def mousePressEvent(self, event) -> None:
        """Expand on click when collapsed."""
        if event.button() == Qt.MouseButton.LeftButton and self._state == DynamicIslandState.COLLAPSED:
            if self._hover_intent_timer.isActive():
                self._hover_intent_timer.stop()
            self.set_state(DynamicIslandState.EXPANDED)
            event.accept()
        else:
            super().mousePressEvent(event)

    def _on_collapse_timer_timeout(self) -> None:
        """Single-shot collapse timer timeout handler."""
        if self._state == DynamicIslandState.EXPANDED and not self._is_pinned:
            self.set_state(DynamicIslandState.COLLAPSED)

    def _on_fullscreen_timer_tick(self) -> None:
        """Periodically check if foreground window is fullscreen and auto-hide/restore overlay."""
        if not self._settings_manager.get_fullscreen_auto_hide():
            if self._suppressed_by_fullscreen:
                self._suppressed_by_fullscreen = False
                if self._state != DynamicIslandState.HIDDEN:
                    self.show()
            return

        screen = self.screen() or QGuiApplication.primaryScreen()
        if not screen:
            return
        dpr = screen.devicePixelRatio() if hasattr(screen, "devicePixelRatio") else 1.0
        geom = screen.geometry()
        screen_rect = (
            int(round(geom.x() * dpr)),
            int(round(geom.y() * dpr)),
            int(round(geom.width() * dpr)),
            int(round(geom.height() * dpr)),
        )
        win_id = int(self.winId()) if self.isVisible() else None

        is_fs = is_foreground_fullscreen(screen_rect, ignore_hwnd=win_id)
        if is_fs and not self._suppressed_by_fullscreen:
            if self.isVisible():
                self._suppressed_by_fullscreen = True
                self.hide()
        elif not is_fs and self._suppressed_by_fullscreen:
            self._suppressed_by_fullscreen = False
            if self._state != DynamicIslandState.HIDDEN:
                self.show()
                self._enforce_topmost_zorder()

    def paintEvent(self, event) -> None:
        """Paint flush top-bezel notch when collapsed and smooth rounded-oval card when expanded."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._ear_radius > 0.0:
            rect = QRectF(self.rect()).adjusted(0.5, 0.0, -0.5, -0.5)
            path = build_desknotch_path(
                rect,
                bottom_radius=self._border_radius,
                ear_radius=self._ear_radius,
            )
            inner_path = build_desknotch_path(
                rect.adjusted(1.0, 0.0, -1.0, -1.0),
                bottom_radius=max(1.0, float(self._border_radius) - 1.0),
                ear_radius=self._ear_radius,
            )
        else:
            rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            radius = min(float(self._border_radius), rect.width() / 2.0, rect.height() / 2.0)
            path = QPainterPath()
            path.addRoundedRect(rect, radius, radius)

            inner_rect = rect.adjusted(1.0, 1.0, -1.0, -1.0)
            inner_radius = min(
                max(1.0, float(self._border_radius) - 1.0),
                inner_rect.width() / 2.0,
                inner_rect.height() / 2.0,
            )
            inner_path = QPainterPath()
            inner_path.addRoundedRect(inner_rect, inner_radius, inner_radius)

        paint_notch_surface(
            painter,
            rect,
            path,
            inner_path,
            self._appearance,
            is_expanded=(self._state == DynamicIslandState.EXPANDED),
            ambient_accent=getattr(self, "_current_accent", None),
        )
        painter.end()

    def compute_top_center_geometry(
        self,
        width: int,
        height: int,
        y_offset: Optional[int] = None,
    ) -> QRect:
        """Calculate top-center QRect on selected screen work area using per-state Y offset."""
        target_monitor = self._settings_manager.get_display_monitor()
        screens = QGuiApplication.screens()
        screen = None

        if target_monitor != "primary" and screens:
            for s in screens:
                if s.name() == target_monitor:
                    screen = s
                    break
            if screen is None and target_monitor.startswith("monitor_"):
                try:
                    idx = int(target_monitor.split("_")[1]) - 1
                    if 0 <= idx < len(screens):
                        screen = screens[idx]
                except (ValueError, IndexError):
                    pass

        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return QRect(0, 0, width, height)
        geom = screen.availableGeometry()
        x = geom.left() + (geom.width() - width) // 2
        offset = y_offset if y_offset is not None else (
            EXPANDED_TOP_OFFSET_PX if self._state == DynamicIslandState.EXPANDED else COLLAPSED_TOP_OFFSET_PX
        )
        y = geom.top() + offset
        return QRect(x, y, width, height)

    def compute_top_center_collapsed_geometry(self) -> QRect:
        """Calculate target top-center QRect for COLLAPSED notch anchored flush at screen top (y = 0)."""
        return self.compute_top_center_geometry(
            COLLAPSED_SIZE[0],
            COLLAPSED_SIZE[1],
            y_offset=COLLAPSED_TOP_OFFSET_PX,
        )

    def _get_expanded_size(self) -> tuple[int, int]:
        """Return target expanded (width, height), adding room for the lyrics strip only when visible."""
        lyrics_visible = (hasattr(self, "lyrics_label") and not self.lyrics_label.isHidden()) or (
            self._settings_manager.get_lyrics_enabled()
            and hasattr(self, "_lyrics_provider")
            and self._lyrics_provider.has_synced_lyrics()
            and self._state == DynamicIslandState.EXPANDED
        )
        extra_h = LYRICS_BAR_EXTRA_HEIGHT if lyrics_visible else 0
        return (EXPANDED_SIZE[0], EXPANDED_SIZE[1] + extra_h)

    def _sync_expanded_geometry(self) -> None:
        """Adjust expanded window height cleanly when the lyrics strip shows or hides."""
        if self._state != DynamicIslandState.EXPANDED:
            return
        if self._geom_anim.state() == QAbstractAnimation.State.Running:
            return
        exp_w, exp_h = self._get_expanded_size()
        if self.width() == exp_w and self.height() == exp_h:
            return
        self._expanded_widget.setFixedSize(exp_w, exp_h)
        self.setFixedSize(exp_w, exp_h)
        self.update_top_center_position(exp_w, exp_h)

    def _apply_lyrics_style(self, accent_color: QColor) -> None:
        """Style dedicated full-width synchronized lyrics banner outside MediaTile."""
        if hasattr(self, "lyrics_label"):
            self.lyrics_label.setStyleSheet(
                f"color: {accent_color.name()};"
                " background-color: rgba(255, 255, 255, 0.04);"
                " border: 1px solid rgba(255, 255, 255, 0.07);"
                " border-radius: 8px;"
                " padding: 2px 10px;"
            )

    def compute_top_center_expanded_geometry(self) -> QRect:
        """Calculate target top-center QRect for EXPANDED floating oval card (y = EXPANDED_TOP_OFFSET_PX)."""
        exp_w, exp_h = self._get_expanded_size()
        return self.compute_top_center_geometry(
            exp_w,
            exp_h,
            y_offset=EXPANDED_TOP_OFFSET_PX,
        )

    def update_top_center_position(self, width: Optional[int] = None, height: Optional[int] = None) -> None:
        """Reposition and resize window to top-center of primary screen work area."""
        if width is not None and height is not None:
            w, h = width, height
        elif self._state == DynamicIslandState.EXPANDED:
            w, h = self._get_expanded_size()
        else:
            w, h = COLLAPSED_SIZE
        y_off = EXPANDED_TOP_OFFSET_PX if self._state == DynamicIslandState.EXPANDED else COLLAPSED_TOP_OFFSET_PX
        target_rect = self.compute_top_center_geometry(w, h, y_offset=y_off)
        self.setGeometry(target_rect)

    def showEvent(self, event) -> None:
        """Ensure top-center position is updated upon window show event."""
        super().showEvent(event)
        self.update_top_center_position()

    def _setup_screen_listeners(self) -> None:
        """Connect dynamic screen addition, removal, and geometry change listeners."""
        app = QGuiApplication.instance()
        if app:
            app.screenAdded.connect(self._on_screens_changed)
            app.screenRemoved.connect(self._on_screens_changed)
            app.primaryScreenChanged.connect(self._on_screens_changed)

        self._connected_screens = set()
        self._bind_screen_geometry_listeners()

    def _bind_screen_geometry_listeners(self) -> None:
        """Attach geometry change listeners to all currently connected display screens."""
        for screen in QGuiApplication.screens():
            if screen not in self._connected_screens:
                screen.geometryChanged.connect(self._on_screen_geometry_changed)
                screen.availableGeometryChanged.connect(self._on_screen_geometry_changed)
                self._connected_screens.add(screen)

    def _on_screens_changed(self, *args) -> None:
        """Handle monitor plug/unplug or primary screen switch."""
        self._bind_screen_geometry_listeners()
        self._on_screen_geometry_changed()

    def _on_screen_geometry_changed(self, *args) -> None:
        """Re-anchor window top-center position when any display geometry changes."""
        if self._state != DynamicIslandState.HIDDEN:
            self.update_top_center_position()
        if hasattr(self, "_lyrics_drawer") and self._lyrics_drawer and self._lyrics_drawer.isVisible():
            self._lyrics_drawer.show_anchored(self.geometry())

    def _toggle_lyrics_drawer(self) -> None:
        """Toggle multi-line synchronized lyrics drawer anchored below expanded card."""
        if not hasattr(self, "_lyrics_drawer") or self._lyrics_drawer is None:
            from src.ui.lyrics_drawer import LyricsDrawerWidget
            self._lyrics_drawer = LyricsDrawerWidget()
            self._lyrics_drawer.seek_requested.connect(self._on_drawer_seek_requested)
            self._lyrics_drawer.set_accent_color(self._current_accent)

        if self._lyrics_drawer.isVisible():
            self._lyrics_drawer.hide_drawer()
        else:
            lines = self._lyrics_provider.get_synced_lines()
            track_title = self.title_label.text() if hasattr(self, "title_label") else ""
            self._lyrics_drawer.set_lyrics(lines, track_title)
            self._lyrics_drawer.set_accent_color(self._current_accent)
            self._lyrics_drawer.set_active_position(self._current_position_ms)
            self._lyrics_drawer.show_anchored(self.geometry())

    def _on_drawer_seek_requested(self, pos_ms: int) -> None:
        """Seek player when user clicks a lyric line in the drawer."""
        if self._media_core:
            self._media_core.seek_to_position(pos_ms)
        self._current_position_ms = pos_ms
        self.progress_slider.setValue(pos_ms)
        self.lbl_position.setText(self._format_time(pos_ms))
        if hasattr(self, "_lyrics_drawer") and self._lyrics_drawer:
            self._lyrics_drawer.set_active_position(pos_ms)

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
        """Generate a crisp 92x92 rounded default placeholder pixmap matching DeskNotch card art."""
        base = QPixmap(92, 92)
        base.fill(QColor(255, 255, 255, 16))
        painter = QPainter(base)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(255, 255, 255, 170))
        font = QFont("Segoe UI", 28, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(base.rect(), Qt.AlignmentFlag.AlignCenter, "♪")
        painter.end()
        return create_rounded_pixmap(base, 92, radius=12.0)

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

    def _update_media_tile_style(self) -> None:
        """Adjust inner #MediaTile frost tint slightly when using bright gradients or custom banners."""
        if not hasattr(self, "_media_tile_frame"):
            return
        if self._appearance.bg_mode in ("gradient", "image"):
            bg_rgba = "rgba(10, 10, 14, 0.28)"
            border_rgba = "rgba(255, 255, 255, 0.14)"
        else:
            bg_rgba = "rgba(255, 255, 255, 0.04)"
            border_rgba = "rgba(255, 255, 255, 0.08)"
        self._media_tile_frame.setStyleSheet(
            "QFrame#MediaTile {"
            f"  background-color: {bg_rgba};"
            f"  border: 1px solid {border_rgba};"
            "  border-radius: 20px;"
            "}"
        )

    def _apply_appearance_colors(self) -> None:
        """Apply configured solid colors, gradients, or custom banner images to notch and expanded card."""
        appearance = NotchAppearance.from_settings(self._settings_manager)
        if self._custom_bg_override:
            appearance = replace(appearance, bg_color=QColor(self._bg_color))
        else:
            self._bg_color = QColor(appearance.bg_color)
        self._border_color = QColor(appearance.border_color)
        self._appearance = appearance

        if hasattr(self, "_capsule_widget"):
            self._capsule_widget.set_appearance(self._appearance)
        if hasattr(self, "_lyrics_drawer") and self._lyrics_drawer:
            self._lyrics_drawer.set_accent_color(self._current_accent)
        self._update_media_tile_style()
        self.update()

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
        elif key == "dynamic_island/hover_intent_delay_ms":
            self._hover_intent_timer.setInterval(int(value))
        elif key == "window/display_monitor":
            self.update_top_center_position()
        elif key == "window/compact_mode":
            if bool(value) != self._is_compact_mode:
                self.set_compact_mode(bool(value))
        elif key == "audio/spectrum_mode":
            if self._media_core and hasattr(self._media_core, "_analyzer") and self._media_core._analyzer:
                self._media_core._analyzer.set_mode(str(value))
        elif key == "features/lyrics_enabled":
            if not bool(value) and hasattr(self, "lyrics_label"):
                self.lyrics_label.hide()
                self._sync_expanded_geometry()
            elif bool(value) and hasattr(self, "lyrics_label"):
                cur_title = str(self.title_label.text() or "").strip()
                cur_artist = str(self.artist_label.text() or "").strip()
                if cur_title and cur_title != "No Media Playing":
                    self._lyrics_provider.fetch_lyrics_async(cur_title, cur_artist, self._duration_ms)
        elif key.startswith("appearance/"):
            if key in ("appearance/collapsed_image_path", "appearance/expanded_image_path"):
                invalidate_banner_cache()
            self._custom_bg_override = False
            self._apply_appearance_colors()

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

        # 2. Expanded Card Container Widget (Oval Capsule Layout)
        self._expanded_widget = QWidget(self)
        expanded_layout = QVBoxLayout(self._expanded_widget)
        expanded_layout.setContentsMargins(18, 12, 18, 12)
        expanded_layout.setSpacing(6)

        # Frosted Inner Glass Media Tile (fixed height so controls never overflow downward)
        self._media_tile_frame = QFrame(self._expanded_widget)
        self._media_tile_frame.setObjectName("MediaTile")
        self._media_tile_frame.setFixedHeight(120)
        self._media_tile_frame.setStyleSheet(
            "QFrame#MediaTile {"
            "  background-color: rgba(255, 255, 255, 0.04);"
            "  border: 1px solid rgba(255, 255, 255, 0.08);"
            "  border-radius: 20px;"
            "}"
        )
        tile_layout = QHBoxLayout(self._media_tile_frame)
        tile_layout.setContentsMargins(10, 10, 10, 10)
        tile_layout.setSpacing(12)

        # Left Column: Rounded Square Album Art Thumbnail (92x92, radius 12px)
        self.art_label = QLabel(self._media_tile_frame)
        self.art_label.setFixedSize(92, 92)
        self.art_label.setPixmap(self._default_art_pixmap)
        self.art_label.setScaledContents(False)
        self.art_label.setStyleSheet("background: transparent; border: none;")

        # Right Column: Header Source Badge, Track Metadata, Transport Controls
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Source Badge Row (Mini Mirrored Bars + Uppercase Player Name + Session Pill + Status Badge)
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 1)
        source_row.setSpacing(5)

        self._visualizer = ReactiveVisualizerWidget(
            bar_count=5, bar_color=self._current_accent, mirrored=True, parent=self._media_tile_frame
        )
        self._visualizer.setFixedSize(22, 11)

        self.lbl_source = QLabel("MEDIADOCK", self._media_tile_frame)
        src_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        src_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        self.lbl_source.setFont(src_font)
        self.lbl_source.setStyleSheet("color: rgba(255, 255, 255, 0.45); background: transparent;")

        self.status_label = QLabel("CLOSED", self._media_tile_frame)
        status_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        self.status_label.setFont(status_font)
        text, text_hex, bg_hex = get_status_badge_style(PlaybackStatus.CLOSED)
        self.status_label.setStyleSheet(
            f"color: {text_hex}; background-color: {bg_hex}; border-radius: 4px; padding: 1px 5px;"
        )

        # Active Session Switcher Pill
        self.combo_sessions = QComboBox(self._media_tile_frame)
        self.combo_sessions.setFixedSize(72, 18)
        self.combo_sessions.setStyleSheet(
            "QComboBox { background-color: rgba(255, 255, 255, 0.08); color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 4px; font-size: 8px; padding: 1px 4px; }"
            "QComboBox::drop-down { border: none; width: 10px; }"
            "QComboBox QAbstractItemView { background-color: #141414; color: #FFFFFF; selection-background-color: #2A2A2A; }"
        )
        self.combo_sessions.currentIndexChanged.connect(self._on_session_combo_changed)
        self.combo_sessions.hide()

        source_row.addWidget(self._visualizer)
        source_row.addWidget(self.lbl_source)
        source_row.addWidget(self.combo_sessions)
        source_row.addStretch()
        source_row.addWidget(self.status_label)

        self.title_label = ElidedLabel("MediaDock", self._media_tile_frame)
        title_font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #FFFFFF; background: transparent;")

        self.artist_label = ElidedLabel("No Media Playing", self._media_tile_frame)
        sub_font = QFont("Segoe UI", 9)
        self.artist_label.setFont(sub_font)
        self.artist_label.setStyleSheet("color: rgba(255, 255, 255, 0.55); background: transparent;")

        # Dedicated Full-Width Synchronized Lyrics Strip (outside MediaTile for full visibility without crowding buttons)
        self.lyrics_label = QLabel("", self._expanded_widget)
        lyrics_font = QFont("Segoe UI")
        lyrics_font.setPointSizeF(8.5)
        lyrics_font.setItalic(True)
        self.lyrics_label.setFont(lyrics_font)
        self.lyrics_label.setWordWrap(True)
        self.lyrics_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lyrics_label.setFixedHeight(32)
        self.lyrics_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lyrics_label.setToolTip("Click to view full synchronized lyrics drawer")
        self.lyrics_label.mousePressEvent = lambda e: self._toggle_lyrics_drawer() if e.button() == Qt.MouseButton.LeftButton else None
        self._apply_lyrics_style(self._current_accent)
        self.lyrics_label.hide()

        # DeskNotch Transport Controls Row
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 2, 0, 0)
        controls_layout.setSpacing(5)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        icon_btn_qss = get_desknotch_icon_button_stylesheet()
        play_btn_qss = get_desknotch_play_button_stylesheet()

        self.btn_prev = QPushButton(self._media_tile_frame)
        self.btn_prev.setFixedSize(26, 26)
        self.btn_prev.setToolTip("Previous Track")
        self.btn_prev.setStyleSheet(icon_btn_qss)
        self.btn_prev.setIcon(get_svg_icon("previous", 14, QColor("#E0E0E0")))
        self.btn_prev.clicked.connect(self._on_btn_prev_clicked)

        # Signature DeskNotch solid white circular Play/Pause disc with pitch-black glyph
        self.btn_play_pause = QPushButton(self._media_tile_frame)
        self.btn_play_pause.setFixedSize(34, 34)
        self.btn_play_pause.setToolTip("Play / Pause")
        self.btn_play_pause.setStyleSheet(play_btn_qss)
        self.btn_play_pause.setIcon(get_svg_icon("play", 16, QColor("#000000")))
        self.btn_play_pause.clicked.connect(self._on_btn_play_pause_clicked)

        self.btn_next = QPushButton(self._media_tile_frame)
        self.btn_next.setFixedSize(26, 26)
        self.btn_next.setToolTip("Next Track")
        self.btn_next.setStyleSheet(icon_btn_qss)
        self.btn_next.setIcon(get_svg_icon("next", 14, QColor("#E0E0E0")))
        self.btn_next.clicked.connect(self._on_btn_next_clicked)

        # Shuffle & Repeat Toggles
        self.btn_shuffle = QPushButton(self._media_tile_frame)
        self.btn_shuffle.setFixedSize(24, 24)
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setToolTip("Shuffle: Off")
        self.btn_shuffle.setStyleSheet(icon_btn_qss)
        self.btn_shuffle.setIcon(get_svg_icon("shuffle", 12, QColor(255, 255, 255, 165)))
        self.btn_shuffle.clicked.connect(self._on_btn_shuffle_clicked)

        self.btn_repeat = QPushButton(self._media_tile_frame)
        self.btn_repeat.setFixedSize(24, 24)
        self.btn_repeat.setCheckable(True)
        self.btn_repeat.setToolTip("Repeat: Off")
        self.btn_repeat.setStyleSheet(icon_btn_qss)
        self.btn_repeat.setIcon(get_svg_icon("repeat", 12, QColor(255, 255, 255, 165)))
        self.btn_repeat.clicked.connect(self._on_btn_repeat_clicked)

        # Volume & Mute Controls
        self.btn_mute = QPushButton(self._media_tile_frame)
        self.btn_mute.setFixedSize(24, 24)
        self.btn_mute.setToolTip("Mute Computer Audio")
        self.btn_mute.setStyleSheet(icon_btn_qss)
        self.btn_mute.setIcon(get_svg_icon("volume", 13, QColor(255, 255, 255, 165)))
        self.btn_mute.clicked.connect(self._on_btn_mute_clicked)

        # VLC-style triangular wedge volume slider (0 to 100%)
        self.slider_volume = VolumeWedgeWidget(self._media_tile_frame, initial_value=100, wedge_width=52, wedge_height=16)
        self.slider_volume.setToolTip("System Volume")
        self.slider_volume.valueChanged.connect(self._on_volume_slider_changed)

        self.lbl_volume_percent = QLabel("100%", self._media_tile_frame)
        self.lbl_volume_percent.setFont(QFont("Segoe UI", 8))
        self.lbl_volume_percent.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 10px; font-weight: 500;")
        self.lbl_volume_percent.setFixedWidth(28)

        # Allow wheel scrolling over mute button to also adjust volume like VLC
        def _mute_wheel_event(event: QWheelEvent) -> None:
            self.slider_volume.wheelEvent(event)
        self.btn_mute.wheelEvent = _mute_wheel_event  # type: ignore[assignment]

        controls_layout.addWidget(self.btn_prev)
        controls_layout.addSpacing(4)
        controls_layout.addWidget(self.btn_play_pause)
        controls_layout.addSpacing(4)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addSpacing(6)
        controls_layout.addWidget(self.btn_shuffle)
        controls_layout.addWidget(self.btn_repeat)
        controls_layout.addSpacing(4)
        controls_layout.addWidget(self.btn_mute)
        controls_layout.addSpacing(2)
        controls_layout.addWidget(self.slider_volume)
        controls_layout.addSpacing(3)
        controls_layout.addWidget(self.lbl_volume_percent)

        info_layout.addLayout(source_row)
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        info_layout.addStretch(1)
        info_layout.addLayout(controls_layout)

        tile_layout.addWidget(self.art_label)
        tile_layout.addLayout(info_layout)

        # Bottom Section: Interactive Timeline Scrub Bar + Action Dock (Pin & Settings)
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(6, 0, 6, 0)
        progress_layout.setSpacing(6)

        time_font = QFont("Segoe UI", 8)

        self.lbl_position = QLabel("00:00", self._expanded_widget)
        self.lbl_position.setFont(time_font)
        self.lbl_position.setStyleSheet("color: rgba(255, 255, 255, 0.50);")

        self.lbl_duration = QLabel("00:00", self._expanded_widget)
        self.lbl_duration.setFont(time_font)
        self.lbl_duration.setStyleSheet("color: rgba(255, 255, 255, 0.50);")

        self.progress_slider = InteractiveScrubSlider(Qt.Orientation.Horizontal, self._expanded_widget)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.setValue(0)
        self.progress_slider.setStyleSheet(get_slider_stylesheet(self._current_accent))

        # Seeking State Machine Connections
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)

        # DeskNotch Action Dock Buttons (Pin/Lock & Settings)
        self.btn_pin = QPushButton(self._expanded_widget)
        self.btn_pin.setFixedSize(24, 24)
        self.btn_pin.setCheckable(True)
        self.btn_pin.setToolTip("Pin Notch Open")
        self.btn_pin.setStyleSheet(icon_btn_qss)
        self.btn_pin.setIcon(get_svg_icon("pin", 12, QColor(255, 255, 255, 165)))
        self.btn_pin.toggled.connect(self._on_btn_pin_toggled)

        self.btn_settings = QPushButton(self._expanded_widget)
        self.btn_settings.setFixedSize(24, 24)
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.setStyleSheet(icon_btn_qss)
        self.btn_settings.setIcon(get_svg_icon("settings", 12, QColor(255, 255, 255, 165)))
        self.btn_settings.clicked.connect(lambda: self.open_settings_requested.emit())

        progress_layout.addWidget(self.lbl_position)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.lbl_duration)
        progress_layout.addWidget(self.btn_pin)
        progress_layout.addWidget(self.btn_settings)

        expanded_layout.addWidget(self._media_tile_frame)
        expanded_layout.addWidget(self.lyrics_label)
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
        if hasattr(self._media_core, "sessions_changed"):
            self._media_core.sessions_changed.connect(self.on_sessions_changed)
        if hasattr(self._media_core, "playback_modes_changed"):
            self._media_core.playback_modes_changed.connect(self.on_playback_modes_changed)

        # Initial display sync
        self.on_track_changed(self._media_core.get_current_track())
        self.on_status_changed(self._media_core.get_playback_status())
        self.on_session_availability_changed(self._media_core.is_session_available())
        self.on_volume_changed(self._media_core.get_volume_state())
        if hasattr(self._media_core, "get_available_sessions"):
            self.on_sessions_changed(self._media_core.get_available_sessions())
        if hasattr(self._media_core, "get_playback_modes"):
            modes = self._media_core.get_playback_modes()
            if isinstance(modes, (tuple, list)) and len(modes) == 2:
                shuf = modes[0] if (modes[0] is None or isinstance(modes[0], bool)) else None
                rep = int(modes[1]) if isinstance(modes[1], int) and not isinstance(modes[1], bool) else 0
                self.on_playback_modes_changed(shuf, rep)


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

    def _on_btn_shuffle_clicked(self) -> None:
        if self._media_core:
            self._media_core.toggle_shuffle()

    def _on_btn_repeat_clicked(self) -> None:
        if self._media_core:
            self._media_core.toggle_repeat()

    def _on_btn_mute_clicked(self) -> None:
        if self._media_core:
            self._media_core.toggle_mute()

    def _on_btn_pin_toggled(self, checked: bool) -> None:
        """Pin or unpin expanded notch open (prevents collapse timeout on mouse leave)."""
        self._is_pinned = checked
        icon_name = "pin_active" if checked else "pin"
        color = QColor("#FFFFFF") if checked else QColor(255, 255, 255, 165)
        self.btn_pin.setIcon(get_svg_icon(icon_name, 12, color))
        if checked and self._collapse_timer.isActive():
            self._collapse_timer.stop()

    def _on_session_combo_changed(self, index: int) -> None:
        """Slot for session selector combo change."""
        if index < 0 or not self._media_core:
            return
        session_id = self.combo_sessions.itemData(index)
        if session_id:
            self._media_core.select_session(session_id)

    def on_sessions_changed(self, sessions: list) -> None:
        """Slot for sessions_changed signal. Updates session switcher dropdown."""
        if not hasattr(self, "combo_sessions"):
            return
        self.combo_sessions.blockSignals(True)
        self.combo_sessions.clear()
        if len(sessions) > 1:
            for s in sessions:
                name = getattr(s, "display_name", "") or getattr(s, "source_name", "Media")
                sid = getattr(s, "session_id", None)
                self.combo_sessions.addItem(name[:12], sid)
                if getattr(s, "is_current", False):
                    self.combo_sessions.setCurrentIndex(self.combo_sessions.count() - 1)
            self.combo_sessions.show()
        else:
            self.combo_sessions.hide()
        self.combo_sessions.blockSignals(False)

    def _on_volume_slider_changed(self, value: int) -> None:
        if hasattr(self, "lbl_volume_percent"):
            self.lbl_volume_percent.setText(f"{value}%")
            self.lbl_volume_percent.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 10px; font-weight: 500;")
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
            if hasattr(self, "lbl_volume_percent"):
                self.lbl_volume_percent.hide()
            return

        self.btn_mute.show()
        self.slider_volume.show()
        if hasattr(self, "lbl_volume_percent"):
            self.lbl_volume_percent.show()

        if hasattr(self.slider_volume, "set_muted"):
            self.slider_volume.set_muted(state.is_muted)

        if not self._is_setting_volume:
            self._is_setting_volume = True
            try:
                self.slider_volume.setValue(state.volume_percent)
            finally:
                self._is_setting_volume = False

        if hasattr(self, "lbl_volume_percent"):
            if state.is_muted:
                self.lbl_volume_percent.setText("0%")
                self.lbl_volume_percent.setStyleSheet("color: rgba(255, 71, 87, 0.85); font-size: 10px; font-weight: 500;")
            else:
                self.lbl_volume_percent.setText(f"{state.volume_percent}%")
                self.lbl_volume_percent.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 10px; font-weight: 500;")

        icon_color = QColor("#C1121C") if state.is_muted else QColor("#FFFFFF")
        icon_name = "mute" if state.is_muted or state.volume_percent == 0 else "volume"
        self.btn_mute.setIcon(get_svg_icon(icon_name, 14, icon_color))
        self.slider_volume.setToolTip(f"System Volume: {state.volume_percent}%")
        self.btn_mute.setToolTip("Unmute Computer Audio" if state.is_muted else "Mute Computer Audio")

    def on_playback_modes_changed(self, shuffle_active: Optional[bool], repeat_mode: int) -> None:
        """Update Shuffle and Repeat button checked states, icons, and tooltips from active session."""
        self._shuffle_active = shuffle_active
        self._repeat_mode = max(0, min(2, int(repeat_mode or 0)))

        muted_col = QColor(255, 255, 255, 165)
        active_col = self._current_accent if hasattr(self, "_current_accent") else QColor("#00FF7F")

        if hasattr(self, "btn_shuffle"):
            shuf_on = bool(shuffle_active)
            self.btn_shuffle.setChecked(shuf_on)
            self.btn_shuffle.setIcon(get_svg_icon("shuffle", 12, active_col if shuf_on else muted_col))
            self.btn_shuffle.setToolTip("Shuffle: On" if shuf_on else "Shuffle: Off")

        if hasattr(self, "btn_repeat"):
            rep_on = self._repeat_mode in (1, 2)
            self.btn_repeat.setChecked(rep_on)
            self.btn_repeat.setIcon(get_svg_icon("repeat", 12, active_col if rep_on else muted_col))
            if self._repeat_mode == 1:
                self.btn_repeat.setToolTip("Repeat: Current Track")
            elif self._repeat_mode == 2:
                self.btn_repeat.setToolTip("Repeat: All / Playlist")
            else:
                self.btn_repeat.setToolTip("Repeat: Off")


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

        if self._settings_manager.get_lyrics_enabled() and self._lyrics_provider.has_synced_lyrics():
            lyric = self._lyrics_provider.get_current_lyric(target_ms)
            self.lyrics_label.setText(f"♪ {lyric}" if lyric else "♪  ♫  ♪")
            if self._state == DynamicIslandState.EXPANDED:
                self.lyrics_label.show()

    # --- UI Position Interpolation Tick ---

    def _on_position_timer_tick(self) -> None:
        """UI-side position interpolation running on 250ms QTimer when PLAYING."""
        if self._current_status != PlaybackStatus.PLAYING:
            return

        elapsed_ms = int((time.monotonic() - self._last_position_update_time) * 1000)
        if self._duration_ms > 0:
            current_pos_ms = min(self._duration_ms, max(0, self._last_position_ms + elapsed_ms))
            self.lbl_position.setText(_format_time_ms(current_pos_ms))
            if not self._is_seeking:
                self.progress_slider.setValue(current_pos_ms)
        else:
            current_pos_ms = max(0, self._last_position_ms + elapsed_ms)
            self.lbl_position.setText(_format_time_ms(current_pos_ms))

        # Update synchronized lyrics preview line in dedicated full-width strip
        was_hidden = self.lyrics_label.isHidden()
        if self._settings_manager.get_lyrics_enabled():
            if self._lyrics_provider.has_synced_lyrics():
                lyric = self._lyrics_provider.get_current_lyric(current_pos_ms)
                self.lyrics_label.setText(f"♪ {lyric}" if lyric else "♪  ♫  ♪")
                if self._state == DynamicIslandState.EXPANDED:
                    self.lyrics_label.show()
                else:
                    self.lyrics_label.hide()
            else:
                self.lyrics_label.hide()
        else:
            self.lyrics_label.hide()
        if was_hidden != self.lyrics_label.isHidden():
            self._sync_expanded_geometry()

        if hasattr(self, "_lyrics_drawer") and self._lyrics_drawer and self._lyrics_drawer.isVisible():
            self._lyrics_drawer.set_active_position(current_pos_ms)

    def _on_lyrics_loaded(self, track_key: str, has_lyrics: bool) -> None:
        """Qt slot invoked on main GUI thread when lyrics finish fetching."""
        if not self._settings_manager.get_lyrics_enabled():
            self.lyrics_label.hide()
            self._sync_expanded_geometry()
            return

        cur_title = str(self.title_label.text() or "").strip()
        cur_artist = str(self.artist_label.text() or "").strip()
        cur_track_key = f"{cur_artist.lower()} - {cur_title.lower()}"

        if track_key != cur_track_key and track_key != f"{self._last_lyric_track_sig[1].lower()} - {self._last_lyric_track_sig[0].lower()}":
            return

        was_hidden = self.lyrics_label.isHidden()
        if has_lyrics:
            elapsed_ms = int((time.monotonic() - self._last_position_update_time) * 1000) if self._current_status == PlaybackStatus.PLAYING else 0
            current_pos_ms = max(0, self._last_position_ms + elapsed_ms)
            if self._duration_ms > 0:
                current_pos_ms = min(self._duration_ms, current_pos_ms)
            lyric = self._lyrics_provider.get_current_lyric(current_pos_ms)
            self.lyrics_label.setText(f"♪ {lyric}" if lyric else "♪  ♫  ♪")
            if self._state == DynamicIslandState.EXPANDED:
                self.lyrics_label.show()
        else:
            self.lyrics_label.hide()

        if was_hidden != self.lyrics_label.isHidden():
            self._sync_expanded_geometry()

        if hasattr(self, "_lyrics_drawer") and self._lyrics_drawer and self._lyrics_drawer.isVisible():
            lines = self._lyrics_provider.get_synced_lines()
            self._lyrics_drawer.set_lyrics(lines, cur_title)
            if has_lyrics:
                self._lyrics_drawer.set_active_position(current_pos_ms)

    # --- Qt Signal Slots ---

    def on_track_changed(self, track: TrackInfo) -> None:
        """Slot for track_changed signal. Updates capsule and expanded track labels."""
        source_name = ""
        if self._media_core and hasattr(self._media_core, "get_active_session_info"):
            try:
                sess = self._media_core.get_active_session_info()
                if sess:
                    cand_disp = getattr(sess, "display_name", "")
                    cand_app = getattr(sess, "app_id", "")
                    if isinstance(cand_disp, str) and cand_disp:
                        source_name = cand_disp
                    elif isinstance(cand_app, str) and cand_app:
                        source_name = cand_app
            except Exception:
                pass
        if not source_name and track and hasattr(track, "app_id") and isinstance(track.app_id, str) and track.app_id:
            source_name = track.app_id

        self._capsule_widget.set_source_info(source_name, str(track.title), str(track.artist))
        self._capsule_widget.set_album_thumbnail(track.album_art_bytes)

        # Format uppercase DeskNotch source label ("SPOTIFY", "YOUTUBE", "VLC", etc.)
        src_key = classify_media_source(source_name, str(track.title), str(track.artist))
        pretty_map = {
            "spotify": "SPOTIFY",
            "youtube": "YOUTUBE",
            "vlc": "VLC",
            "default_media": source_name.split("!")[0].replace(".exe", "").upper() if source_name else "MEDIADOCK",
        }
        self._current_source_display = str(pretty_map.get(src_key, "MEDIADOCK") or "MEDIADOCK")
        self._refresh_source_label()

        # Update expanded card metadata
        self.title_label.setText(track.title)
        self.artist_label.setText(track.artist)
        self._update_album_art(track.album_art_bytes)

        track_sig = (str(track.title or ""), str(track.artist or ""))
        if track_sig != self._last_lyric_track_sig:
            self._last_lyric_track_sig = track_sig
            self.lyrics_label.clear()
            self.lyrics_label.hide()
            self._sync_expanded_geometry()
            if hasattr(self, "_lyrics_drawer") and self._lyrics_drawer and self._lyrics_drawer.isVisible():
                self._lyrics_drawer.set_lyrics([], str(track.title or ""))

        # Trigger synchronized lyrics fetch
        if self._settings_manager.get_lyrics_enabled() and track and track.title:
            self._lyrics_provider.fetch_lyrics_async(track.title, track.artist, track.duration_ms)

        # Dynamic album art accent extraction & styling
        self._current_accent = extract_dominant_color(track.album_art_bytes)
        self.progress_slider.setStyleSheet(get_slider_stylesheet(self._current_accent))
        self.slider_volume.setStyleSheet(get_slider_stylesheet(self._current_accent))
        self._capsule_widget.set_accent_color(self._current_accent)
        self._visualizer.set_bar_color(self._current_accent)
        self._apply_lyrics_style(self._current_accent)
        if hasattr(self, "_lyrics_drawer") and self._lyrics_drawer:
            self._lyrics_drawer.set_accent_color(self._current_accent)
        self.on_playback_modes_changed(self._shuffle_active, self._repeat_mode)
        self.update()

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
            self.progress_slider.setValue(min(self._last_position_ms, self._duration_ms) if self._duration_ms > 0 else self._last_position_ms)

        # Ensure position timer is ticking if currently playing
        if self._current_status == PlaybackStatus.PLAYING and not self._position_timer.isActive():
            self._position_timer.start()

        # Trigger smooth opacity transition
        self._trigger_track_fade_animation()

    def _refresh_source_label(self) -> None:
        """Update uppercase tracked player header label ('SPOTIFY' vs 'PAUSED · SPOTIFY')."""
        if not hasattr(self, "lbl_source"):
            return
        name = self._current_source_display or "MEDIADOCK"
        if self._current_status == PlaybackStatus.PLAYING:
            self.lbl_source.setText(name)
        elif self._current_status == PlaybackStatus.PAUSED:
            self.lbl_source.setText(f"PAUSED · {name}")
        else:
            self.lbl_source.setText(name)

    def on_audio_visualizer_updated(self, bars: list) -> None:
        """Slot for audio_visualizer_updated signal. Updates visualizer bar heights during active playback."""
        if self._current_status == PlaybackStatus.PLAYING:
            self._visualizer.set_bar_heights(bars)
            self._capsule_widget.set_bar_heights(bars)

    def on_status_changed(self, status: PlaybackStatus) -> None:
        """Slot for playback_status_changed signal. Updates badge, capsule, and visualizer."""
        self._current_status = status

        self._capsule_widget.set_playback_status(status)
        self._visualizer.set_playback_status(status)
        self._refresh_source_label()

        text, text_hex, bg_hex = get_status_badge_style(status)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {text_hex}; background-color: {bg_hex}; border-radius: 4px; padding: 1px 5px;"
        )

        if status == PlaybackStatus.PLAYING:
            self.btn_play_pause.setIcon(get_svg_icon("pause", 16, QColor("#000000")))
            if not self._position_timer.isActive():
                self._position_timer.start()
            if (
                self._settings_manager.get_dynamic_island_enabled()
                and self._state == DynamicIslandState.HIDDEN
                and not self._manually_hidden
                and not self._suppressed_by_fullscreen
            ):
                self.set_state(DynamicIslandState.COLLAPSED)
            elif self.isVisible():
                self._enforce_topmost_zorder()
        elif status in (PlaybackStatus.PAUSED, PlaybackStatus.STOPPED, PlaybackStatus.CLOSED):
            self.btn_play_pause.setIcon(get_svg_icon("play", 16, QColor("#000000")))
            if self._position_timer.isActive():
                self._position_timer.stop()
            self._visualizer.clear_bar_heights()

    def on_session_availability_changed(self, available: bool) -> None:
        """Slot for session_availability_changed signal. Updates control state & Dynamic Island visibility."""
        self.btn_prev.setEnabled(available)
        self.btn_play_pause.setEnabled(available)
        self.btn_next.setEnabled(available)
        self.btn_shuffle.setEnabled(available)
        self.btn_repeat.setEnabled(available)
        self.progress_slider.setEnabled(available)

        if available:
            self._manually_hidden = False
            if self._settings_manager.get_dynamic_island_enabled():
                if self._state == DynamicIslandState.HIDDEN:
                    self.set_state(DynamicIslandState.COLLAPSED)
                elif not self.isVisible() and not self._suppressed_by_fullscreen:
                    self.show()
                self._enforce_topmost_zorder()
        else:
            if self._position_timer.isActive():
                self._position_timer.stop()
            self.on_track_changed(TrackInfo.empty())
            self.on_status_changed(PlaybackStatus.CLOSED)
            # Session closed -> transition to HIDDEN while process remains alive
            self.set_state(DynamicIslandState.HIDDEN)

    def _update_album_art(self, art_bytes: Optional[bytes]) -> None:
        """Load raw image bytes into rounded 92x92 QPixmap matching DeskNotch artwork tile."""
        if art_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(art_bytes):
                self.art_label.setPixmap(create_rounded_pixmap(pixmap, 92, radius=12.0))
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
