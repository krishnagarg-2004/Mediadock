"""Frameless window base class with rounded corners, translucent background, and drag support."""

from typing import Optional
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QPaintEvent, QPainter, QPainterPath, QColor
from PySide6.QtWidgets import QWidget


class FramelessWindow(QWidget):
    """Base QWidget class for borderless, draggable, always-on-top windows."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        border_radius: float = 16.0,
        bg_color: QColor = QColor("#1E1E2E"),
    ) -> None:
        super().__init__(parent)
        self._border_radius = border_radius
        self._bg_color = bg_color
        self._drag_pos: Optional[QPoint] = None

        self._setup_window_flags()

    def _setup_window_flags(self) -> None:
        """Configure Qt window flags for frameless, always-on-top, and translucent display."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Record the drag start position when left mouse button is pressed."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Move the window based on mouse drag delta."""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Reset drag tracking on left mouse button release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint an anti-aliased rounded rectangle background for the window."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(
            self.rect().adjusted(0, 0, 0, 0),
            self._border_radius,
            self._border_radius,
        )

        painter.fillPath(path, self._bg_color)
