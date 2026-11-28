"""Reusable UI widget components for MediaDock."""

from typing import Optional, Callable
from PySide6.QtCore import Qt, QPoint, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QResizeEvent,
    QMouseEvent,
    QWheelEvent,
    QPainter,
    QPainterPath,
    QColor,
    QLinearGradient,
    QPen,
    QBrush,
)
from PySide6.QtWidgets import QLabel, QWidget, QSlider, QToolTip


class ElidedLabel(QLabel):
    """QLabel subclass that automatically elides text on the right when overflowing."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._full_text = text
        self._update_elided_text()

    def setText(self, text: str) -> None:
        """Store full text and update rendered elided display."""
        self._full_text = text
        self._update_elided_text()

    def full_text(self) -> str:
        """Return the un-elided full text string."""
        return self._full_text

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Re-evaluate text elision when label dimensions change."""
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self) -> None:
        """Compute elided text string for current label width."""
        if not self._full_text:
            super().setText("")
            self.setToolTip("")
            return

        available_width = self.width()
        if available_width <= 0:
            super().setText(self._full_text)
            return

        elided = self.fontMetrics().elidedText(
            self._full_text,
            Qt.TextElideMode.ElideRight,
            available_width,
        )
        super().setText(elided)
        if elided != self._full_text:
            self.setToolTip(self._full_text)
        else:
            self.setToolTip("")


class InteractiveScrubSlider(QSlider):
    """QSlider subclass with click-to-seek, smooth scrubbing, and live timestamp tooltip."""

    def __init__(
        self,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        parent: Optional[QWidget] = None,
        tooltip_formatter: Optional[Callable[[int], str]] = None,
    ) -> None:
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self._tooltip_formatter = tooltip_formatter or self._default_time_format

    @staticmethod
    def _default_time_format(val_ms: int) -> str:
        total_sec = max(0, val_ms // 1000)
        return f"{total_sec // 60:02d}:{total_sec % 60:02d}"

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Jump slider immediately to clicked position and start scrubbing."""
        if event.button() == Qt.MouseButton.LeftButton:
            w = max(1, self.width())
            ratio = max(0.0, min(1.0, event.position().x() / w))
            new_val = int(self.minimum() + ratio * (self.maximum() - self.minimum()))
            self.setValue(new_val)
            self.sliderPressed.emit()
            self.sliderMoved.emit(new_val)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update live scrub position on drag and show position preview tooltip on hover."""
        w = max(1, self.width())
        ratio = max(0.0, min(1.0, event.position().x() / w))
        hover_val = int(self.minimum() + ratio * (self.maximum() - self.minimum()))

        if event.buttons() & Qt.MouseButton.LeftButton:
            self.setValue(hover_val)
            self.sliderMoved.emit(hover_val)

        # Update hover preview tooltip
        formatted_time = self._tooltip_formatter(hover_val)
        self.setToolTip(formatted_time)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Complete scrubbing operation and emit sliderReleased."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.sliderReleased.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class VolumeWedgeWidget(QWidget):
    """VLC-style upward-sloping triangular wedge volume slider (0 to 100%).
    
    Supports:
    - Click-to-seek and smooth horizontal drag-scrubbing
    - Mouse wheel scrolling (like VLC: +/- 5% per scroll tick)
    - Full VLC chromatic ramp (Green -> Yellow -> Amber -> Coral/Red at 100%)
    - Muted desaturated/grayed state
    - Drop-in interface compatibility with QSlider (value, setValue, valueChanged, setRange)
    """

    valueChanged = Signal(int)
    sliderMoved = Signal(int)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_value: int = 100,
        wedge_width: int = 56,
        wedge_height: int = 16,
    ) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._min: int = 0
        self._max: int = 100
        self._value: int = max(0, min(100, int(initial_value)))
        self._is_muted: bool = False
        self._is_dragging: bool = False
        self._accent_color: Optional[QColor] = None

        self._wedge_w = wedge_width
        self._wedge_h = wedge_height
        self.setFixedSize(self._wedge_w + 4, self._wedge_h + 4)
        self._update_tooltip()

    def value(self) -> int:
        """Return current volume percentage (0 to 100)."""
        return self._value

    def setValue(self, val: int) -> None:
        """Set volume percentage clamped to 0–100% and trigger repaint."""
        clamped = max(self._min, min(self._max, int(val)))
        if clamped != self._value:
            self._value = clamped
            self._update_tooltip()
            self.valueChanged.emit(clamped)
            self.update()

    def minimum(self) -> int:
        return self._min

    def maximum(self) -> int:
        return self._max

    def setMinimum(self, val: int) -> None:
        self._min = max(0, int(val))

    def setMaximum(self, val: int) -> None:
        self._max = max(1, int(val))

    def setRange(self, min_val: int, max_val: int) -> None:
        self._min = max(0, int(min_val))
        self._max = max(1, int(max_val))

    def set_muted(self, muted: bool) -> None:
        """Update muted state for desaturated/dimmed rendering."""
        if self._is_muted != muted:
            self._is_muted = muted
            self._update_tooltip()
            self.update()

    def is_muted(self) -> bool:
        return self._is_muted

    def set_accent_color(self, color: Optional[QColor]) -> None:
        """Optionally override the chromatic ramp with the track accent color."""
        self._accent_color = color
        self.update()

    def setStyleSheet(self, qss: str) -> None:
        """No-op for custom-rendered wedge (preserves QSlider stylesheet calls)."""
        pass

    def _update_tooltip(self) -> None:
        status = "Muted" if self._is_muted else f"{self._value}%"
        self.setToolTip(f"System Volume: {status} (Scroll or Click to adjust)")

    def _pos_to_val(self, pos_x: float) -> int:
        pad_x = 2.0
        avail_w = max(1.0, float(self.width()) - 2 * pad_x)
        ratio = max(0.0, min(1.0, (pos_x - pad_x) / avail_w))
        return int(round(self._min + ratio * (self._max - self._min)))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            new_val = self._pos_to_val(event.position().x())
            self.setValue(new_val)
            self.valueChanged.emit(new_val)
            self.sliderMoved.emit(new_val)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            new_val = self._pos_to_val(event.position().x())
            if new_val != self._value:
                self.setValue(new_val)
                self.valueChanged.emit(new_val)
                self.sliderMoved.emit(new_val)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Adjust volume smoothly on mouse wheel (like VLC: 5% per scroll step)."""
        delta = event.angleDelta().y()
        if delta == 0:
            delta = event.angleDelta().x()
        step = 5 if delta > 0 else -5
        new_val = max(self._min, min(self._max, self._value + step))
        if new_val != self._value:
            self.setValue(new_val)
            self.valueChanged.emit(new_val)
            self.sliderMoved.emit(new_val)
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        pad_x = 2.0
        pad_y = 2.0

        left = pad_x
        right = w - pad_x
        bottom = h - pad_y
        top_right = pad_y
        # Slanted wedge: left edge is thin (3.5px tall), right edge is maximum height
        h_min = 3.5
        top_left = bottom - h_min

        # Construct wedge polygon path
        wedge_path = QPainterPath()
        wedge_path.moveTo(left, top_left)
        wedge_path.lineTo(right, top_right)
        wedge_path.lineTo(right, bottom)
        wedge_path.lineTo(left, bottom)
        wedge_path.closeSubpath()

        # 1. Unfilled Background Track (dark translucent glass)
        painter.fillPath(wedge_path, QBrush(QColor(0, 0, 0, 95)))
        painter.strokePath(wedge_path, QPen(QColor(255, 255, 255, 40), 1.0))

        # 2. Filled Level (clipped to current percentage)
        if self._value > self._min:
            ratio = max(0.0, min(1.0, float(self._value - self._min) / float(max(1, self._max - self._min))))
            fill_x = left + ratio * (right - left)

            painter.save()
            painter.setClipPath(wedge_path)
            painter.setClipRect(QRectF(0, 0, fill_x, h), Qt.ClipOperation.IntersectClip)

            if self._is_muted:
                # Muted state: soft grayed-out glass
                painter.fillRect(QRectF(0, 0, w, h), QBrush(QColor(255, 255, 255, 45)))
            else:
                # Classic VLC chromatic ramp:
                # Green (low) -> Yellow (mid) -> Amber (high) -> Coral/Red (100%)
                grad = QLinearGradient(left, 0, right, 0)
                grad.setColorAt(0.0, QColor("#00FF7F"))   # Vibrant green
                grad.setColorAt(0.48, QColor("#2ECC71"))  # Emerald green
                grad.setColorAt(0.72, QColor("#F1C40F"))  # Sun yellow
                grad.setColorAt(0.88, QColor("#E67E22"))  # Amber
                grad.setColorAt(1.0, QColor("#FF4757"))   # Coral red at 100%
                painter.fillRect(QRectF(0, 0, w, h), grad)

            painter.restore()

            # Crisp outline stroke over the filled path
            painter.strokePath(wedge_path, QPen(QColor(255, 255, 255, 70), 1.0))

            # Luminous white leading tick mark at the current volume level
            if fill_x > left + 1.0 and fill_x < right - 1.0:
                t = (fill_x - left) / (right - left)
                cur_y_top = top_left + t * (top_right - top_left)
                line_pen = QPen(QColor(255, 255, 255, 220), 1.5)
                painter.setPen(line_pen)
                painter.drawLine(QPointF(fill_x, cur_y_top), QPointF(fill_x, bottom))

