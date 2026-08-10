"""Windows system tray icon component for MediaDock."""

from typing import Optional
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from src.core.models import TrackInfo, PlaybackStatus
from src.core.media_core import MediaCore
from src.ui.theme import COLOR_BG_BASE, COLOR_ACCENT_BLUE, COLOR_TEXT_PRIMARY


def create_tray_icon_pixmap(size: int = 32) -> QPixmap:
    """Generate a crisp vector-style in-memory QPixmap icon for the system tray."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw rounded background badge (Catppuccin Base #1E1E2E)
    painter.setBrush(COLOR_BG_BASE)
    painter.setPen(COLOR_ACCENT_BLUE)
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 6, 6)

    # Draw centered musical note glyph '♪'
    painter.setPen(COLOR_TEXT_PRIMARY)
    font = QFont("Segoe UI", int(size * 0.45), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "♪")
    painter.end()

    return pixmap


class SystemTrayIcon(QSystemTrayIcon):
    """System tray icon component with context menu, click activation, and dynamic tooltip."""

    show_hide_requested = Signal()
    compact_mode_requested = Signal(bool)
    show_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(
        self,
        media_core: Optional[MediaCore] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        icon = QIcon(create_tray_icon_pixmap(32))
        super().__init__(icon, parent)

        self._media_core = media_core
        self.setToolTip("MediaDock - No Media Playing")

        self._init_menu()
        self.activated.connect(self._on_tray_activated)

        if self._media_core:
            self._connect_media_core()

    def _init_menu(self) -> None:
        """Create tray context menu with Show/Hide, Compact Mode, Media Source, Settings, and Exit actions."""
        self._menu = QMenu()

        self.action_show_hide = QAction("Show MediaDock", self._menu)
        self.action_show_hide.triggered.connect(self.show_hide_requested.emit)

        self.action_compact_mode = QAction("Compact Mode", self._menu)
        self.action_compact_mode.setCheckable(True)
        self.action_compact_mode.triggered.connect(
            lambda checked: self.compact_mode_requested.emit(checked)
        )

        self.menu_media_source = QMenu("Media Source", self._menu)

        self.action_settings = QAction("Settings...", self._menu)
        self.action_settings.triggered.connect(self.settings_requested.emit)

        self.action_exit = QAction("Exit MediaDock", self._menu)
        self.action_exit.triggered.connect(self.exit_requested.emit)

        self._menu.addAction(self.action_show_hide)
        self._menu.addAction(self.action_compact_mode)
        self._menu.addMenu(self.menu_media_source)
        self._menu.addAction(self.action_settings)
        self._menu.addSeparator()
        self._menu.addAction(self.action_exit)

        self.setContextMenu(self._menu)

    def set_compact_mode_checked(self, enabled: bool) -> None:
        """Update Compact Mode checkable action state to remain synchronized with settings/window."""
        self.action_compact_mode.setChecked(enabled)

    def hide_tray_icon(self) -> None:
        """Explicitly hide tray icon to prevent ghost icon artifacts in Windows notification area on shutdown."""
        self.hide()

    def _connect_media_core(self) -> None:
        """Connect MediaCore signals to update tooltip and session selection dynamically."""
        if not self._media_core:
            return

        self._media_core.track_changed.connect(self._on_track_changed)
        self._media_core.playback_status_changed.connect(self._on_status_changed)
        self._media_core.session_availability_changed.connect(
            self._on_session_availability_changed
        )
        self._media_core.sessions_changed.connect(self._on_sessions_changed)

        # Initial sync
        self._update_tooltip(
            self._media_core.get_current_track(),
            self._media_core.get_playback_status(),
            self._media_core.is_session_available(),
        )
        self._on_sessions_changed(self._media_core.get_available_sessions())

    def _on_sessions_changed(self, sessions: list) -> None:
        """Update Media Source context submenu with available sessions."""
        self.menu_media_source.clear()

        selected_id = (
            self._media_core.get_selected_session_id() if self._media_core else None
        )

        # Default automatic selection action
        auto_action = QAction("Auto (System Default)", self.menu_media_source)
        auto_action.setCheckable(True)
        auto_action.setChecked(selected_id is None)
        auto_action.triggered.connect(
            lambda: self._media_core.select_session(None) if self._media_core else None
        )
        self.menu_media_source.addAction(auto_action)

        if sessions:
            self.menu_media_source.addSeparator()
            for info in sessions:
                action = QAction(info.display_name, self.menu_media_source)
                action.setCheckable(True)
                action.setChecked(info.is_selected)
                session_id = info.session_id
                action.triggered.connect(
                    lambda _, s_id=session_id: self._media_core.select_session(s_id)
                    if self._media_core
                    else None
                )
                self.menu_media_source.addAction(action)


    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle left click (Trigger) to toggle and double click to bring window to front."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_hide_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_requested.emit()


    def _on_track_changed(self, track: TrackInfo) -> None:
        status = (
            self._media_core.get_playback_status()
            if self._media_core
            else PlaybackStatus.CLOSED
        )
        available = (
            self._media_core.is_session_available() if self._media_core else False
        )
        self._update_tooltip(track, status, available)

    def _on_status_changed(self, status: PlaybackStatus) -> None:
        track = (
            self._media_core.get_current_track()
            if self._media_core
            else TrackInfo.empty()
        )
        available = (
            self._media_core.is_session_available() if self._media_core else False
        )
        self._update_tooltip(track, status, available)

    def _on_session_availability_changed(self, available: bool) -> None:
        track = (
            self._media_core.get_current_track()
            if self._media_core and available
            else TrackInfo.empty()
        )
        status = (
            self._media_core.get_playback_status()
            if self._media_core and available
            else PlaybackStatus.CLOSED
        )
        self._update_tooltip(track, status, available)

    def _update_tooltip(
        self, track: TrackInfo, status: PlaybackStatus, available: bool = True
    ) -> None:
        """Format dynamic tray tooltip string."""
        if (
            not available
            or status == PlaybackStatus.CLOSED
            or not track.title
            or track.title == "No Media Playing"
        ):
            self.setToolTip("MediaDock - No Media Playing")
        else:
            self.setToolTip(f"MediaDock - {track.title} by {track.artist} [{status.value}]")

    def update_menu_state(self, window_visible: bool) -> None:
        """Update Show/Hide menu action text depending on window visibility."""
        if window_visible:
            self.action_show_hide.setText("Hide MediaDock")
        else:
            self.action_show_hide.setText("Show MediaDock")
