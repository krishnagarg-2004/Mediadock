"""Frameless window base class with rounded corners, translucent background, and drag support."""

from typing import Optional
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QPaintEvent, QPainter, QPainterPath, QColor, QGuiApplication, QScreen
from PySide6.QtWidgets import QWidget


SNAP_THRESHOLD_PX = 15


class FramelessWindow(QWidget):
    """Base QWidget class for borderless, draggable, always-on-top windows."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        border_radius: float = 16.0,
        bg_color: QColor = QColor("#000000"),
        allow_drag: bool = True,
    ) -> None:
        super().__init__(parent)
        self._border_radius = border_radius
        self._bg_color = bg_color
        self._allow_drag = allow_drag
        self._drag_pos: Optional[QPoint] = None

        self._setup_window_flags()

    @property
    def allow_drag(self) -> bool:
        """Return True if free mouse dragging is enabled for this window."""
        return self._allow_drag

    @allow_drag.setter
    def allow_drag(self, enabled: bool) -> None:
        """Enable or disable free mouse dragging for this window."""
        self._allow_drag = enabled

    def _setup_window_flags(self) -> None:
        """Configure Qt window flags for frameless, always-on-top, and translucent display."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _apply_edge_snapping(self, raw_pos: QPoint) -> QPoint:
        """Calculate snapped position against screen availableGeometry within 15px threshold."""
        win_w = self.width()
        win_h = self.height()
        target_center = QPoint(raw_pos.x() + win_w // 2, raw_pos.y() + win_h // 2)

        screen = QGuiApplication.screenAt(target_center) or QGuiApplication.primaryScreen()
        if screen is None:
            return raw_pos

        geom = screen.availableGeometry()
        snapped_x = raw_pos.x()
        snapped_y = raw_pos.y()

        # Left edge snap
        if abs(snapped_x - geom.left()) <= SNAP_THRESHOLD_PX:
            snapped_x = geom.left()
        # Right edge snap
        elif abs((snapped_x + win_w) - geom.right()) <= SNAP_THRESHOLD_PX:
            snapped_x = geom.right() - win_w

        # Top edge snap
        if abs(snapped_y - geom.top()) <= SNAP_THRESHOLD_PX:
            snapped_y = geom.top()
        # Bottom edge snap
        elif abs((snapped_y + win_h) - geom.bottom()) <= SNAP_THRESHOLD_PX:
            snapped_y = geom.bottom() - win_h

        return QPoint(snapped_x, snapped_y)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Record the drag start position when left mouse button is pressed and drag is enabled."""
        if self._allow_drag and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Move the window based on mouse drag delta if drag is enabled."""
        if self._allow_drag and event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            raw_pos = event.globalPosition().toPoint() - self._drag_pos
            snapped_pos = self._apply_edge_snapping(raw_pos)
            self.move(snapped_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Reset drag tracking on left mouse button release."""
        if self._allow_drag and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint an anti-aliased notch shape (flat top edge against screen bezel, rounded bottom corners) and subtle border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(0, 0, -1, -1)
        r = float(self._border_radius)
        path = QPainterPath()
        path.moveTo(rect.left(), rect.top())
        path.lineTo(rect.right(), rect.top())
        path.lineTo(rect.right(), rect.bottom() - r)
        path.quadTo(rect.right(), rect.bottom(), rect.right() - r, rect.bottom())
        path.lineTo(rect.left() + r, rect.bottom())
        path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - r)
        path.closeSubpath()

        painter.fillPath(path, self._bg_color)

        # Pure Black 1px border stroke (#000000)
        from PySide6.QtGui import QPen
        pen = QPen(QColor("#000000"), 1)
        painter.setPen(pen)
        painter.drawPath(path)
