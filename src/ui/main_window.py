"""Main application widget window for MediaDock."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from src.ui.frameless_window import FramelessWindow


class MainWindow(FramelessWindow):
    """Main floating widget window for MediaDock."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        border_radius: float = 16.0,
        bg_color: QColor = QColor("#1E1E2E"),
    ) -> None:
        super().__init__(parent, border_radius=border_radius, bg_color=bg_color)
        self.setWindowTitle("MediaDock")
        self.resize(340, 120)

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI layout and placeholder contents."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(6)

        title_label = QLabel("MediaDock", self)
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #FFFFFF;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Milestone 1 — Foundation", self)
        sub_font = QFont("Segoe UI", 10)
        subtitle_label.setFont(sub_font)
        subtitle_label.setStyleSheet("color: #A6ADC8;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint_label = QLabel("(Drag to move • Press Esc to close)", self)
        hint_font = QFont("Segoe UI", 8)
        hint_label.setFont(hint_font)
        hint_label.setStyleSheet("color: #6C7086;")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(hint_label)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Close window on Escape key press."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)
