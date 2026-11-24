"""Reusable UI widget components for MediaDock."""

from typing import Optional, Callable
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QResizeEvent, QMouseEvent
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
