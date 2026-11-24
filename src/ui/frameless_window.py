"""Frameless window base class with DeskNotch obsidian glass shell, flared concave top ears, and rounded bottom corners."""

from typing import Optional
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import (
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QColor,
    QGuiApplication,
    QLinearGradient,
    QPen,
)
from PySide6.QtWidgets import QWidget


SNAP_THRESHOLD_PX = 15


def build_desknotch_path(
    rect: QRectF,
    bottom_radius: float = 16.0,
    ear_radius: float = 8.0,
) -> QPainterPath:
    """Construct MacBook / DeskNotch silhouette with top flared concave ears and bottom convex curves."""
    x0, y0 = rect.left(), rect.top()
    x1, y1 = rect.right(), rect.bottom()
    ear = min(float(ear_radius), max(0.0, (rect.width() - 4.0) / 4.0), max(0.0, rect.height() / 3.0))
    r = min(float(bottom_radius), max(0.0, (rect.width() - 2.0 * ear) / 2.0), max(0.0, rect.height() - ear))

    path = QPainterPath()
    if ear > 0.5:
        path.moveTo(x0, y0)
        path.lineTo(x1, y0)
        # Right inverted concave ear transitioning smoothly to vertical notch wall
        path.quadTo(x1 - ear, y0, x1 - ear, y0 + ear)
        path.lineTo(x1 - ear, y1 - r)
        path.quadTo(x1 - ear, y1, x1 - ear - r, y1)
        path.lineTo(x0 + ear + r, y1)
        path.quadTo(x0 + ear, y1, x0 + ear, y1 - r)
        path.lineTo(x0 + ear, y0 + ear)
        # Left inverted concave ear flaring outward to top bezel
        path.quadTo(x0 + ear, y0, x0, y0)
        path.closeSubpath()
    else:
        path.moveTo(x0, y0)
        path.lineTo(x1, y0)
        path.lineTo(x1, y1 - r)
        path.quadTo(x1, y1, x1 - r, y1)
        path.lineTo(x0 + r, y1)
        path.quadTo(x0, y1, x0, y1 - r)
        path.closeSubpath()
    return path


class FramelessWindow(QWidget):
    """Base QWidget class for borderless, draggable, always-on-top windows."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        border_radius: float = 14.0,
        ear_radius: float = 8.0,
        bg_color: QColor = QColor("#000000"),
        allow_drag: bool = True,
    ) -> None:
        super().__init__(parent)
        self._border_radius = border_radius
        self._ear_radius = ear_radius
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
        """Paint anti-aliased DeskNotch obsidian glass shell with top flared ears and edge light-catch."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.0, -0.5, -0.5)
        path = build_desknotch_path(rect, bottom_radius=self._border_radius, ear_radius=self._ear_radius)

        # Obsidian black hardware shell base
        painter.fillPath(path, self._bg_color)

        # DeskNotch layered translucent frost sheen (lighter at top edge)
        sheen = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 14))
        sheen.setColorAt(0.45, QColor(255, 255, 255, 5))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 2))
        painter.fillPath(path, sheen)

        # Subtle hairline border stroke for definition against light/dark backgrounds
        pen = QPen(QColor(255, 255, 255, 22), 1.0)
        painter.setPen(pen)
        painter.drawPath(path)
