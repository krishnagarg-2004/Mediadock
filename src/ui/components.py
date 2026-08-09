"""Reusable UI widget components for MediaDock."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QLabel, QWidget


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
