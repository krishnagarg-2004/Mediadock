"""Translucent floating multi-line synchronized lyrics drawer for MediaDock."""

from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QEvent
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
)

from src.media.lyrics_provider import LyricsLine
from src.ui.theme import (
    COLOR_BG_BASE,
    COLOR_BG_SURFACE,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT_GREEN,
    get_button_stylesheet,
)


class ClickableLyricLine(QLabel):
    """Clickable lyric line row supporting tap-to-seek."""

    clicked = Signal(int)

    def __init__(self, time_ms: int, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.time_ms = time_ms
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Segoe UI", 11))
        self.setContentsMargins(12, 6, 12, 6)
        self.setStyleSheet(
            "color: rgba(255, 255, 255, 0.60);"
            "border-radius: 8px;"
            "background-color: transparent;"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.time_ms)
        super().mousePressEvent(event)


class LyricsDrawerWidget(QWidget):
    """Translucent floating multi-line synchronized lyrics viewer with auto-scroll and seek."""

    seek_requested = Signal(int)
    closed = Signal()

    DRAWER_WIDTH: int = 410
    DRAWER_HEIGHT: int = 280

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.DRAWER_WIDTH, self.DRAWER_HEIGHT)

        self._lines: List[LyricsLine] = []
        self._line_widgets: List[ClickableLyricLine] = []
        self._active_index: int = -1
        self._accent_color: QColor = COLOR_ACCENT_GREEN

        self._init_ui()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Main translucent frosted container card
        self._card = QFrame(self)
        self._card.setObjectName("LyricsCard")
        self._card.setStyleSheet(
            "#LyricsCard {"
            "  background-color: rgba(14, 14, 20, 0.94);"
            "  border: 1px solid rgba(255, 255, 255, 0.14);"
            "  border-radius: 16px;"
            "}"
        )
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        # Header bar
        header = QHBoxLayout()
        header.setContentsMargins(6, 0, 4, 0)

        self.lbl_header_title = QLabel("♪ Synchronized Lyrics", self._card)
        self.lbl_header_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_header_title.setStyleSheet("color: #FFFFFF;")

        self.btn_close = QPushButton("✕", self._card)
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "QPushButton {"
            "  background: rgba(255, 255, 255, 0.08);"
            "  color: #FFFFFF;"
            "  border: none;"
            "  border-radius: 11px;"
            "  font-size: 10px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.20); }"
        )
        self.btn_close.clicked.connect(self.hide_drawer)

        header.addWidget(self.lbl_header_title)
        header.addStretch()
        header.addWidget(self.btn_close)
        card_layout.addLayout(header)

        # Subtle divider line
        divider = QFrame(self._card)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none;")
        card_layout.addWidget(divider)

        # Scrollable lyrics area
        self._scroll = QScrollArea(self._card)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical {"
            "  background: transparent;"
            "  width: 4px;"
            "  margin: 0px;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: rgba(255, 255, 255, 0.22);"
            "  border-radius: 2px;"
            "  min-height: 20px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "  height: 0px;"
            "}"
        )
        self._scroll.viewport().setStyleSheet("background: transparent;")

        self._lines_container = QWidget()
        self._lines_container.setStyleSheet("background: transparent;")
        self._lines_layout = QVBoxLayout(self._lines_container)
        self._lines_layout.setContentsMargins(4, 40, 4, 40)
        self._lines_layout.setSpacing(4)

        self.lbl_empty = QLabel("No synchronized lyrics available", self._lines_container)
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty.setStyleSheet("color: rgba(255, 255, 255, 0.40); font-size: 12px;")
        self._lines_layout.addWidget(self.lbl_empty)

        self._scroll.setWidget(self._lines_container)
        card_layout.addWidget(self._scroll, 1)

        root_layout.addWidget(self._card)

    def set_accent_color(self, color: QColor) -> None:
        """Update active lyrics highlight color."""
        self._accent_color = color
        self._refresh_highlight()

    def set_lyrics(self, lines: List[LyricsLine], track_title: str = "") -> None:
        """Load lyrics timeline and populate clickable rows."""
        self._lines = lines
        self._active_index = -1

        # Clear existing line widgets
        for w in self._line_widgets:
            w.deleteLater()
        self._line_widgets.clear()

        if track_title:
            self.lbl_header_title.setText(f"♪ {track_title}")
        else:
            self.lbl_header_title.setText("♪ Synchronized Lyrics")

        if not lines:
            self.lbl_empty.show()
            return

        self.lbl_empty.hide()

        for line in lines:
            display_text = line.text if line.text.strip() else "♪"
            line_widget = ClickableLyricLine(line.time_ms, display_text, self._lines_container)
            line_widget.clicked.connect(self.seek_requested.emit)
            self._lines_layout.addWidget(line_widget)
            self._line_widgets.append(line_widget)

    def set_active_position(self, position_ms: int) -> None:
        """Update active line highlighting and smoothly auto-scroll."""
        if not self._lines or not self._line_widgets:
            return

        active_idx = -1
        for idx, line in enumerate(self._lines):
            if line.time_ms <= position_ms:
                active_idx = idx
            else:
                break

        if active_idx != self._active_index:
            self._active_index = active_idx
            self._refresh_highlight()
            self._scroll_to_active()

    def _refresh_highlight(self) -> None:
        """Apply active and inactive typography styling to lyrics lines."""
        accent_hex = self._accent_color.name()

        for idx, widget in enumerate(self._line_widgets):
            if idx == self._active_index:
                # Active line: large, bold, accent colored, pill background
                widget.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                widget.setStyleSheet(
                    f"color: {accent_hex};"
                    f"background-color: rgba(255, 255, 255, 0.10);"
                    f"border: 1px solid rgba(255, 255, 255, 0.16);"
                    "border-radius: 8px;"
                    "padding: 6px 12px;"
                )
            elif idx < self._active_index:
                # Past lines: dimmed
                widget.setFont(QFont("Segoe UI", 10))
                widget.setStyleSheet(
                    "color: rgba(255, 255, 255, 0.35);"
                    "background-color: transparent;"
                    "border: none;"
                    "padding: 4px 12px;"
                )
            else:
                # Upcoming lines: legible, subtle
                widget.setFont(QFont("Segoe UI", 10))
                widget.setStyleSheet(
                    "color: rgba(255, 255, 255, 0.70);"
                    "background-color: transparent;"
                    "border: none;"
                    "padding: 4px 12px;"
                )

    def _scroll_to_active(self) -> None:
        """Center the active lyrics line within the scroll view."""
        if 0 <= self._active_index < len(self._line_widgets):
            target_widget = self._line_widgets[self._active_index]
            widget_y = target_widget.geometry().center().y()
            viewport_h = self._scroll.viewport().height()
            target_scroll = max(0, widget_y - viewport_h // 2)
            self._scroll.verticalScrollBar().setValue(target_scroll)

    def show_anchored(self, anchor_rect: QRect) -> None:
        """Show drawer anchored directly below the expanded media notch card."""
        x = anchor_rect.left() + (anchor_rect.width() - self.DRAWER_WIDTH) // 2
        y = anchor_rect.bottom() + 8
        self.move(x, y)
        self.show()
        self._scroll_to_active()

    def hide_drawer(self) -> None:
        """Hide drawer and notify parent."""
        self.hide()
        self.closed.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide_drawer()
            event.accept()
        else:
            super().keyPressEvent(event)
