import ctypes
import math
import sys
from typing import Optional, Any, Dict, List, Tuple
from PySide6.QtCore import Qt, Signal, QUrl, __version__ as QT_RUNTIME_VERSION
from PySide6.QtGui import QFont, QKeyEvent, QColor, QDesktopServices, QGuiApplication, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
    QFrame,
    QSpinBox,
    QSlider,
    QComboBox,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
)

from src.core.settings import SettingsManager, parse_hex_color
from src.media.equalizer_apo import EqualizerAPOManager, EQUALIZER_APO_DOWNLOAD_URL
from src.ui.theme import (
    COLOR_BG_BASE,
    COLOR_BG_MANTLE,
    COLOR_BG_SURFACE,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GREEN,
    get_button_stylesheet,
)

GITHUB_REPO_URL = "https://github.com/krishnagarg-2004/Mediadock"
GITHUB_ISSUES_URL = "https://github.com/krishnagarg-2004/Mediadock/issues"

EQ_PRESETS: Dict[str, List[float]] = {
    "Flat": [0.0, 0.0, 0.0, 0.0, 0.0],
    "Bass Boost": [5.0, 3.5, 0.0, 0.0, 0.0],
    "Vocal Clarity": [-2.0, 1.0, 4.0, 3.0, 1.0],
    "Electronic": [4.5, 3.0, -1.0, 2.5, 4.5],
    "Rock": [4.0, 2.0, -0.5, 2.0, 3.5],
    "Acoustic": [2.5, 1.0, 2.0, 2.5, 3.0],
}


class ShortcutRecorderWidget(QWidget):
    """Interactive key-capture shortcut recorder supporting strictly 2-key and 3-key global hotkeys."""

    sequenceChanged = Signal(str)

    def __init__(self, sequence: str = "Ctrl+Alt+S", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._sequence: str = sequence
        self._is_recording: bool = False
        self._validation_error: str = ""

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)
        self.setMinimumWidth(320)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        self.pills_widget = QWidget(self)
        self.pills_layout = QHBoxLayout(self.pills_widget)
        self.pills_layout.setContentsMargins(0, 0, 0, 0)
        self.pills_layout.setSpacing(6)

        self.lbl_status = QLabel(self)
        self.lbl_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        self.btn_record = QPushButton("Record", self)
        self.btn_record.setFixedSize(65, 26)
        self.btn_record.setStyleSheet(get_button_stylesheet())
        self.btn_record.clicked.connect(self.start_recording)

        self.btn_clear = QPushButton("✕", self)
        self.btn_clear.setFixedSize(26, 26)
        self.btn_clear.setStyleSheet(get_button_stylesheet())
        self.btn_clear.clicked.connect(self.clear_sequence)

        layout.addWidget(self.pills_widget)
        layout.addWidget(self.lbl_status, 1)
        layout.addWidget(self.btn_record)
        layout.addWidget(self.btn_clear)

        self.update_display()

    def sequence(self) -> str:
        return self._sequence

    def set_sequence(self, sequence: str) -> None:
        self._sequence = sequence
        self._validation_error = ""
        self._is_recording = False
        self.update_display()

    def text(self) -> str:
        """Backward compatibility accessor for QLineEdit.text()."""
        return self._sequence

    def setText(self, text: str) -> None:
        """Backward compatibility setter for QLineEdit.setText()."""
        self.set_sequence(text)

    def validation_error(self) -> str:
        return self._validation_error

    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(self) -> None:
        self._is_recording = True
        self._validation_error = ""
        self.setFocus()
        self.update_display()

    def clear_sequence(self) -> None:
        self._sequence = ""
        self._validation_error = ""
        self._is_recording = False
        self.update_display()
        self.sequenceChanged.emit("")

    def update_display(self) -> None:
        # Clear existing pill items
        while self.pills_layout.count():
            item = self.pills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._is_recording:
            self.lbl_status.setText("Press 2 or 3 keys...")
            self.lbl_status.setStyleSheet("color: #89B4FA; font-size: 11px;")
            self.pills_widget.hide()
            self.lbl_status.show()
            self.setStyleSheet(
                f"ShortcutRecorderWidget {{ background-color: {COLOR_BG_MANTLE.name()}; border: 2px solid {COLOR_ACCENT_BLUE.name()}; border-radius: 6px; }}"
            )
        else:
            self.lbl_status.hide()
            self.pills_widget.show()
            tokens = [t.strip() for t in self._sequence.split("+") if t.strip()]
            for idx, token in enumerate(tokens):
                if idx > 0:
                    plus_lbl = QLabel("+", self.pills_widget)
                    plus_lbl.setStyleSheet("color: #A6ADC8; font-size: 12px; font-weight: bold; padding: 0 4px;")
                    self.pills_layout.addWidget(plus_lbl)

                pill = QLabel(token, self.pills_widget)
                pill.setStyleSheet(
                    "QLabel {"
                    "  background-color: #313244;"
                    "  color: #CDD6F4;"
                    "  border: 1px solid #45475A;"
                    "  border-top: 1px solid #585B70;"
                    "  border-radius: 4px;"
                    "  font-family: 'Segoe UI', sans-serif;"
                    "  font-size: 11px;"
                    "  font-weight: bold;"
                    "  padding: 3px 10px;"
                    "}"
                )
                self.pills_layout.addWidget(pill)

            self.pills_layout.addStretch()

            border_col = "#F38BA8" if self._validation_error else COLOR_BORDER.name()
            self.setStyleSheet(
                f"ShortcutRecorderWidget {{ background-color: {COLOR_BG_SURFACE.name()}; border: 1px solid {border_col}; border-radius: 6px; }}"
            )

    def mousePressEvent(self, event) -> None:
        if not self._is_recording:
            self.start_recording()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._is_recording:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Escape and modifiers == Qt.KeyboardModifier.NoModifier:
            self._is_recording = False
            self.update_display()
            event.accept()
            return

        tokens = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            tokens.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            tokens.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            tokens.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            tokens.append("Win")

        main_key_str = ""
        if key not in (
            Qt.Key.Key_Control,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
            Qt.Key.Key_AltGr,
        ):
            if key == Qt.Key.Key_Space:
                main_key_str = "Space"
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                main_key_str = "Enter"
            elif key == Qt.Key.Key_Tab:
                main_key_str = "Tab"
            elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
                main_key_str = f"F{key - Qt.Key.Key_F1 + 1}"
            else:
                txt = event.text().upper()
                if txt and txt.isalnum():
                    main_key_str = txt
                else:
                    from PySide6.QtGui import QKeySequence
                    seq_str = QKeySequence(key).toString()
                    if seq_str and len(seq_str) == 1 and seq_str.isalnum():
                        main_key_str = seq_str.upper()

        if main_key_str:
            tokens.append(main_key_str)

        if not main_key_str:
            return

        key_count = len(tokens)

        # STRICT VALIDATION: Only 2-key and 3-key shortcuts allowed
        if key_count < 2:
            self._validation_error = "Shortcuts must contain at least 2 keys (e.g. Ctrl+S or Ctrl+Alt+S)."
            self._is_recording = False
            self.update_display()
            return

        if key_count > 3:
            self._validation_error = "Shortcuts cannot exceed 3 keys."
            self._is_recording = False
            self.update_display()
            return

        new_seq = "+".join(tokens)
        self._sequence = new_seq
        self._validation_error = ""
        self._is_recording = False
        self.update_display()
        self.sequenceChanged.emit(new_seq)
        event.accept()


class CollapseDelaySpinBox(QSpinBox):
    """Numeric QSpinBox control for Collapse Delay with read-only text entry and stacked ▲/▼ buttons."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setRange(500, 30000)
        self.setSingleStep(250)
        self.setSuffix(" ms")
        self.setFixedWidth(130)
        self.setFixedHeight(32)

        # Read-only numeric display to keyboard text entry
        line_edit = self.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Hide native spinbox buttons via QSS
        self.setStyleSheet(
            "QSpinBox {"
            f"  background-color: {COLOR_BG_SURFACE.name()};"
            f"  color: {COLOR_TEXT_PRIMARY.name()};"
            f"  border: 1px solid {COLOR_BORDER.name()};"
            "  border-radius: 6px;"
            "  padding-left: 10px;"
            "  padding-right: 34px;"
            "  font-family: 'Segoe UI', sans-serif;"
            "  font-size: 12px;"
            "}"
            "QSpinBox::up-button, QSpinBox::down-button {"
            "  width: 0px; height: 0px; border: none;"
            "}"
        )

        # Equal-sized stacked ▲ and ▼ buttons
        self._btn_container = QWidget(self)
        btn_layout = QVBoxLayout(self._btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(0)

        btn_style = (
            "QPushButton {"
            f"  background-color: {COLOR_BG_MANTLE.name()};"
            f"  color: {COLOR_TEXT_PRIMARY.name()};"
            f"  border-left: 1px solid {COLOR_BORDER.name()};"
            "  border-top: none; border-right: none; border-bottom: none;"
            "  font-size: 8px;"
            "  padding: 0px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #45475A;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #585B70;"
            "}"
        )

        self.btn_up = QPushButton("▲", self._btn_container)
        self.btn_up.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_up.setStyleSheet(
            btn_style + f"QPushButton {{ border-bottom: 1px solid {COLOR_BORDER.name()}; border-top-right-radius: 5px; }}"
        )
        self.btn_up.clicked.connect(self.stepUp)

        self.btn_down = QPushButton("▼", self._btn_container)
        self.btn_down.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_down.setStyleSheet(
            btn_style + "QPushButton { border-bottom-right-radius: 5px; }"
        )
        self.btn_down.clicked.connect(self.stepDown)

        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)

        self._update_button_geometry()

    def _update_button_geometry(self) -> None:
        """Positions stacked buttons dynamically along right edge with equal geometry."""
        h = max(20, self.height() - 2)
        half_h = h // 2
        self._btn_container.setGeometry(self.width() - 29, 1, 28, h)
        self.btn_up.setFixedHeight(half_h)
        self.btn_down.setFixedHeight(h - half_h)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_button_geometry()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Ignore text typing so value can only be changed via spin buttons or arrow navigation."""
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_PageUp):
            self.stepUp()
            event.accept()
        elif event.key() in (Qt.Key.Key_Down, Qt.Key.Key_PageDown):
            self.stepDown()
            event.accept()
        else:
            event.ignore()


class SettingsDialog(QDialog):
    """Spacious frosted Gaussian-blur landscape Preferences dialog with card-based scrollable pages."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        hotkey_manager: Optional[Any] = None,
        media_core: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._settings_manager = settings_manager
        self._hotkey_manager = hotkey_manager
        self._media_core = media_core
        self._apo_manager = EqualizerAPOManager()
        self._is_updating_ui = False
        self._blur_backdrop_mode: str = "none"

        self.setWindowTitle("MediaDock Preferences")
        self.setMinimumSize(780, 560)
        self.resize(820, 600)
        self.setSizeGripEnabled(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._init_ui()
        self._apply_gaussian_blur_backdrop()
        self.load_settings()

    def _apply_gaussian_blur_backdrop(self) -> None:
        """Enable hardware Windows Gaussian Blur (Win11 Acrylic backdrop with Win10 composition fallback)."""
        if sys.platform != "win32":
            self._blur_backdrop_mode = "translucent"
            return

        try:
            hwnd = int(self.winId())
            dwmapi = ctypes.windll.dwmapi

            # Enable dark window frame & rounded corners
            dark_mode = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
            corner_pref = ctypes.c_int(2)  # DWMWCP_ROUND
            dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))

            class _MARGINS(ctypes.Structure):
                _fields_ = [
                    ("cxLeftWidth", ctypes.c_int),
                    ("cxRightWidth", ctypes.c_int),
                    ("cyTopHeight", ctypes.c_int),
                    ("cyBottomHeight", ctypes.c_int),
                ]

            margins = _MARGINS(-1, -1, -1, -1)
            dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

            # Windows 11 22H2+ native Acrylic Gaussian Blur (DWMSBT_TRANSIENTWINDOW = 3)
            backdrop_type = ctypes.c_int(3)
            hr = dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop_type), ctypes.sizeof(backdrop_type))
            if hr == 0:
                self._blur_backdrop_mode = "dwm_acrylic"
                return

            # Fallback for older Windows 10/11 builds via SetWindowCompositionAttribute
            class _ACCENT_POLICY(ctypes.Structure):
                _fields_ = [
                    ("AccentState", ctypes.c_int),
                    ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_uint),
                    ("AnimationId", ctypes.c_int),
                ]

            class _WINCOMPATTRDATA(ctypes.Structure):
                _fields_ = [
                    ("Attribute", ctypes.c_int),
                    ("Data", ctypes.POINTER(_ACCENT_POLICY)),
                    ("SizeOfData", ctypes.c_size_t),
                ]

            policy = _ACCENT_POLICY(4, 2, 0x99101015, 0)  # ACCENT_ENABLE_ACRYLICBLURBEHIND
            comp_data = _WINCOMPATTRDATA(19, ctypes.pointer(policy), ctypes.sizeof(policy))
            res = ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(comp_data))
            if res:
                self._blur_backdrop_mode = "composition_acrylic"
        except Exception:
            self._blur_backdrop_mode = "translucent"

    def paintEvent(self, event) -> None:
        """Paint translucent dark frosted glass veil so DWM Gaussian blur composites cleanly."""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(12, 12, 16, 152))
        painter.end()

    def _create_scrollable_page(self, title: str, subtitle: str) -> Tuple[QWidget, QVBoxLayout]:
        """Build a standardized settings page with fixed header and spacious scrollable body."""
        page = QWidget(self.stacked_widget)
        page.setStyleSheet("background: transparent;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(10)

        header = QWidget(page)
        header.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(2, 0, 2, 0)
        header_layout.setSpacing(3)

        lbl_title = QLabel(title, header)
        lbl_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        header_layout.addWidget(lbl_title)

        lbl_sub = QLabel(subtitle, header)
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        lbl_sub.setWordWrap(True)
        header_layout.addWidget(lbl_sub)

        page_layout.addWidget(header)

        divider = QFrame(page)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.10); border: none;")
        page_layout.addWidget(divider)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(2, 4, 12, 12)
        content_layout.setSpacing(12)

        scroll.setWidget(container)
        page_layout.addWidget(scroll, 1)
        return page, content_layout

    def _create_setting_card(
        self, parent: QWidget, section_title: Optional[str] = None
    ) -> Tuple[QFrame, QVBoxLayout]:
        """Create a rounded container card so individual options never compete for space."""
        card = QFrame(parent)
        card.setObjectName("SettingCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(12)

        if section_title:
            lbl_sec = QLabel(section_title, card)
            lbl_sec.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_sec.setStyleSheet("color: #D4D4DC; letter-spacing: 0.4px;")
            card_layout.addWidget(lbl_sec)

        return card, card_layout

    def _add_toggle_block(
        self, card_layout: QVBoxLayout, checkbox: QCheckBox, description: str
    ) -> QLabel:
        """Add a comfortably spaced checkbox row with wrapped subtitle text below it."""
        block = QWidget()
        block_l = QVBoxLayout(block)
        block_l.setContentsMargins(0, 2, 0, 2)
        block_l.setSpacing(3)

        checkbox.setMinimumHeight(24)
        block_l.addWidget(checkbox)

        lbl_desc = QLabel(description, block)
        lbl_desc.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 26px;"
        )
        lbl_desc.setWordWrap(True)
        block_l.addWidget(lbl_desc)

        card_layout.addWidget(block)
        return lbl_desc

    def _add_control_row(
        self,
        card_layout: QVBoxLayout,
        title: str,
        control: QWidget,
        description: str = "",
        extra_controls: Optional[List[QWidget]] = None,
    ) -> None:
        """Place label/subtitle on the left and fixed control(s) cleanly on the right."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(3)

        lbl_title = QLabel(title, row_widget)
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()}; font-size: 12px; font-weight: 600;")
        text_col.addWidget(lbl_title)

        if description:
            lbl_desc = QLabel(description, row_widget)
            lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
            lbl_desc.setWordWrap(True)
            text_col.addWidget(lbl_desc)

        row_layout.addLayout(text_col, 1)

        ctrl_container = QHBoxLayout()
        ctrl_container.setContentsMargins(0, 0, 0, 0)
        ctrl_container.setSpacing(8)
        if extra_controls:
            for extra in extra_controls:
                ctrl_container.addWidget(extra, 0, Qt.AlignmentFlag.AlignVCenter)
        ctrl_container.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)

        row_layout.addLayout(ctrl_container)
        card_layout.addWidget(row_widget)

    def _init_ui(self) -> None:
        """Initialize translucent frosted-glass sidebar navigation, cards, and dialog controls."""
        self.setStyleSheet(
            f"QDialog {{ background-color: transparent; color: {COLOR_TEXT_PRIMARY.name()}; }}"
            "QStackedWidget, QLabel { background-color: transparent; }"
            "QFrame#SettingCard {"
            "  background-color: rgba(255, 255, 255, 0.055);"
            "  border: 1px solid rgba(255, 255, 255, 0.11);"
            "  border-radius: 12px;"
            "}"
            "QCheckBox {"
            f"  color: {COLOR_TEXT_PRIMARY.name()};"
            "  background: transparent;"
            "  font-family: 'Segoe UI', sans-serif;"
            "  font-size: 12px;"
            "  font-weight: 600;"
            "  spacing: 8px;"
            "}"
            "QCheckBox::indicator {"
            "  width: 17px;"
            "  height: 17px;"
            "  border-radius: 4px;"
            "  border: 1px solid rgba(255, 255, 255, 0.24);"
            "  background-color: rgba(255, 255, 255, 0.07);"
            "}"
            "QCheckBox::indicator:hover {"
            f"  border-color: {COLOR_ACCENT_GREEN.name()};"
            "}"
            "QCheckBox::indicator:checked {"
            f"  background-color: {COLOR_ACCENT_GREEN.name()};"
            f"  border-color: {COLOR_ACCENT_GREEN.name()};"
            "}"
            "QComboBox {"
            "  background-color: rgba(20, 20, 28, 0.72);"
            "  border: 1px solid rgba(255, 255, 255, 0.15);"
            "  border-radius: 7px;"
            "  padding: 5px 10px;"
            f"  color: {COLOR_TEXT_PRIMARY.name()};"
            "  font-size: 12px;"
            "  min-height: 22px;"
            "}"
            "QComboBox:hover, QLineEdit:hover {"
            "  border-color: rgba(255, 255, 255, 0.30);"
            "}"
            "QComboBox QAbstractItemView {"
            "  background-color: #16161E;"
            f"  color: {COLOR_TEXT_PRIMARY.name()};"
            "  border: 1px solid rgba(255, 255, 255, 0.16);"
            "  selection-background-color: rgba(255, 255, 255, 0.14);"
            "}"
            "QLineEdit {"
            "  background-color: rgba(20, 20, 28, 0.72);"
            "  border: 1px solid rgba(255, 255, 255, 0.15);"
            "  border-radius: 7px;"
            "  padding: 6px 10px;"
            f"  color: {COLOR_TEXT_PRIMARY.name()};"
            "  font-size: 12px;"
            "}"
            "QLineEdit:focus {"
            f"  border: 1px solid {COLOR_ACCENT_GREEN.name()};"
            "}"
            "QScrollBar:vertical {"
            "  background: transparent;"
            "  width: 8px;"
            "  margin: 2px 0px 2px 0px;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: rgba(255, 255, 255, 0.18);"
            "  border-radius: 4px;"
            "  min-height: 28px;"
            "}"
            "QScrollBar::handle:vertical:hover {"
            "  background: rgba(255, 255, 255, 0.30);"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "  height: 0px;"
            "}"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {"
            "  background: none;"
            "}"
        )

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # 1. Persistent Left Navigation Sidebar (185px) — Frosted Glass
        self.sidebar = QListWidget(self)
        self.sidebar.setFixedWidth(185)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.setStyleSheet(
            "QListWidget {"
            "  background-color: rgba(255, 255, 255, 0.045);"
            "  border: 1px solid rgba(255, 255, 255, 0.10);"
            "  border-radius: 12px;"
            "  padding: 8px;"
            f"  color: {COLOR_TEXT_PRIMARY.name()};"
            "  font-family: 'Segoe UI', sans-serif;"
            "  font-size: 12px;"
            "  outline: 0;"
            "}"
            "QListWidget::item {"
            "  height: 40px;"
            "  padding-left: 14px;"
            "  border-radius: 8px;"
            "  margin-bottom: 4px;"
            "  border: none;"
            "}"
            "QListWidget::item:selected {"
            "  background-color: rgba(255, 255, 255, 0.11);"
            "  color: #FFFFFF;"
            "  font-weight: bold;"
            f"  border-left: 3px solid {COLOR_ACCENT_GREEN.name()};"
            "}"
            "QListWidget::item:hover:!selected {"
            "  background-color: rgba(255, 255, 255, 0.06);"
            "  color: #FFFFFF;"
            "}"
            "QListWidget:focus {"
            "  outline: none;"
            "}"
        )

        pages_list = [
            "Preferences",
            "Global Shortcuts",
            "Dynamic Island",
            "Appearance",
            "Audio",
            "About",
        ]

        for page_title in pages_list:
            item = QListWidgetItem(page_title, self.sidebar)
            self.sidebar.addItem(item)

        root_layout.addWidget(self.sidebar)

        # 2. Right Content Area Container
        right_container = QWidget(self)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # QStackedWidget for Page switching
        self.stacked_widget = QStackedWidget(right_container)

        # Page 0: General Preferences
        page_prefs, layout_prefs = self._create_scrollable_page(
            "General Preferences",
            "Manage Windows startup behavior, window visibility, monitor target, and synchronized lyrics.",
        )

        card_startup, layout_startup = self._create_setting_card(page_prefs, "Startup & System Tray")
        self.chk_autostart_windows = QCheckBox("Start with Windows", card_startup)
        self.lbl_autostart_windows_desc = self._add_toggle_block(
            layout_startup,
            self.chk_autostart_windows,
            "Automatically launch MediaDock when you log into Windows.",
        )
        self.chk_start_hidden = QCheckBox("Start Minimized to Tray", card_startup)
        self.lbl_start_hidden_desc = self._add_toggle_block(
            layout_startup,
            self.chk_start_hidden,
            "Start silently in the system tray without immediately displaying the notch.",
        )
        self.chk_close_to_tray = QCheckBox("Close to System Tray", card_startup)
        self.lbl_close_to_tray_desc = self._add_toggle_block(
            layout_startup,
            self.chk_close_to_tray,
            "Keep MediaDock running in the system tray when closing the overlay instead of exiting.",
        )
        layout_prefs.addWidget(card_startup)

        card_display, layout_display = self._create_setting_card(page_prefs, "Window & Display")
        self.chk_always_on_top = QCheckBox("Always On Top", card_display)
        self.lbl_always_on_top_desc = self._add_toggle_block(
            layout_display,
            self.chk_always_on_top,
            "Keep the Dynamic Island notch floating above other application windows.",
        )
        self.chk_dynamic_island = QCheckBox("Enable Dynamic Island (Top Notch)", card_display)
        self.lbl_dynamic_island_desc = self._add_toggle_block(
            layout_display,
            self.chk_dynamic_island,
            "Anchor the ambient media notch at the top-center bezel of the selected screen.",
        )
        self.chk_fullscreen_auto_hide = QCheckBox("Auto-Hide in Fullscreen Games & Apps", card_display)
        self.lbl_fullscreen_auto_hide_desc = self._add_toggle_block(
            layout_display,
            self.chk_fullscreen_auto_hide,
            "Suppress the top notch overlay automatically while gaming or watching fullscreen videos.",
        )
        self.combo_display_monitor = QComboBox(card_display)
        self.combo_display_monitor.setFixedWidth(220)
        self.combo_display_monitor.addItem("Primary Monitor", "primary")
        screens = QGuiApplication.screens()
        for idx, scr in enumerate(screens):
            self.combo_display_monitor.addItem(f"Monitor {idx + 1} ({scr.name()})", scr.name())
        self._add_control_row(
            layout_display,
            "Target Display Monitor",
            self.combo_display_monitor,
            "Choose which screen displays the top-center Dynamic Island overlay.",
        )
        layout_prefs.addWidget(card_display)

        card_media, layout_media = self._create_setting_card(page_prefs, "Media Experience")
        self.chk_lyrics_enabled = QCheckBox("Enable Live Synchronized Lyrics", card_media)
        self.lbl_lyrics_desc = self._add_toggle_block(
            layout_media,
            self.chk_lyrics_enabled,
            "Display synced lyrics inside the expanded media card when matching lyrics are found.",
        )
        layout_prefs.addWidget(card_media)
        layout_prefs.addStretch(1)

        self.stacked_widget.addWidget(page_prefs)

        # Page 1: Global Shortcuts
        page_hk, layout_hk = self._create_scrollable_page(
            "Global Shortcuts",
            "Configure system-wide keyboard shortcuts using a 2-key or 3-key modifier combination.",
        )

        card_hk, layout_hk_card = self._create_setting_card(page_hk, "Shortcut Bindings")
        self.rec_hotkey_show_hide = ShortcutRecorderWidget("Ctrl+Alt+S", card_hk)
        self.rec_hotkey_show_hide.setMinimumWidth(250)
        self._add_control_row(
            layout_hk_card,
            "Show / Hide Overlay",
            self.rec_hotkey_show_hide,
            "Toggle the Dynamic Island overlay visibility from anywhere on the desktop.",
        )

        self.rec_hotkey_play_pause = ShortcutRecorderWidget("Ctrl+Alt+Space", card_hk)
        self.rec_hotkey_play_pause.setMinimumWidth(250)
        self._add_control_row(
            layout_hk_card,
            "Play / Pause Media",
            self.rec_hotkey_play_pause,
            "Toggle playback on the active Windows media session globally.",
        )

        self.lbl_error = QLabel("", card_hk)
        self.lbl_error.setStyleSheet("color: #F38BA8; font-size: 11px; padding-top: 4px;")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        layout_hk_card.addWidget(self.lbl_error)
        layout_hk.addWidget(card_hk)

        card_hk_tips, layout_hk_tips = self._create_setting_card(page_hk, "Shortcut Guidelines")
        lbl_hk_tip = QLabel(
            "Click any shortcut box and press your desired combination (for example: Ctrl+Alt+S or Ctrl+Shift+Space).\n"
            "Press Esc while recording to cancel. Shortcuts require 1+ modifier key (Ctrl, Alt, Shift, Win) and total 2 or 3 keys.",
            card_hk_tips,
        )
        lbl_hk_tip.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; line-height: 1.4;")
        lbl_hk_tip.setWordWrap(True)
        layout_hk_tips.addWidget(lbl_hk_tip)
        layout_hk.addWidget(card_hk_tips)
        layout_hk.addStretch(1)

        self.stacked_widget.addWidget(page_hk)

        # Page 2: Dynamic Island Settings
        page_di, layout_di = self._create_scrollable_page(
            "Dynamic Island",
            "Fine-tune how the notch expands on interaction and when it returns to compact view.",
        )

        card_expand, layout_expand = self._create_setting_card(page_di, "Expansion Interaction")
        self.combo_expand_trigger = QComboBox(card_expand)
        self.combo_expand_trigger.setFixedWidth(180)
        self.combo_expand_trigger.addItem("Hover to Expand", "hover")
        self.combo_expand_trigger.addItem("Click to Expand", "click")
        self._add_control_row(
            layout_expand,
            "Expansion Trigger",
            self.combo_expand_trigger,
            "Open the expanded media player either on mouse hover or explicit click.",
        )

        self.spn_hover_intent = QSpinBox(card_expand)
        self.spn_hover_intent.setRange(0, 1000)
        self.spn_hover_intent.setSingleStep(50)
        self.spn_hover_intent.setSuffix(" ms")
        self.spn_hover_intent.setFixedWidth(140)
        self.spn_hover_intent.setFixedHeight(32)
        self._add_control_row(
            layout_expand,
            "Hover Intent Delay",
            self.spn_hover_intent,
            "Delay before hover expands the notch, reducing accidental expansion near the top bezel.",
        )
        layout_di.addWidget(card_expand)

        card_collapse, layout_collapse = self._create_setting_card(page_di, "Auto-Collapse Timing")
        self.spn_collapse_delay = CollapseDelaySpinBox(card_collapse)
        self.spn_collapse_delay.setFixedWidth(140)
        self.spn_collapse_delay.setFixedHeight(32)
        self._add_control_row(
            layout_collapse,
            "Collapse Delay",
            self.spn_collapse_delay,
            "Time in milliseconds before the expanded card automatically collapses after pointer leaves.",
        )
        layout_di.addWidget(card_collapse)
        layout_di.addStretch(1)

        self.stacked_widget.addWidget(page_di)

        # Page 3: Appearance (Hex Background & Border Only — No Status Colors)
        page_app, layout_app = self._create_scrollable_page(
            "Appearance",
            "Customize the Dynamic Island background and border colors directly using 6-digit hex color codes.",
        )

        card_colors, layout_colors = self._create_setting_card(page_app, "Custom Hex Colors")

        self.swatch_bg_preview = QFrame(card_colors)
        self.swatch_bg_preview.setFixedSize(34, 34)
        self.txt_bg_color_hex = QLineEdit(card_colors)
        self.txt_bg_color_hex.setFixedSize(124, 34)
        self.txt_bg_color_hex.setMaxLength(7)
        self.txt_bg_color_hex.setPlaceholderText("#000000")
        self.txt_bg_color_hex.setFont(QFont("Consolas", 11))
        self.txt_bg_color_hex.textChanged.connect(self._on_appearance_hex_changed)
        self._add_control_row(
            layout_colors,
            "Background Color (Hex)",
            self.txt_bg_color_hex,
            "Fill color used by the Dynamic Island capsule and expanded card (e.g. #000000 or #0E1117).",
            extra_controls=[self.swatch_bg_preview],
        )

        self.swatch_border_preview = QFrame(card_colors)
        self.swatch_border_preview.setFixedSize(34, 34)
        self.txt_border_color_hex = QLineEdit(card_colors)
        self.txt_border_color_hex.setFixedSize(124, 34)
        self.txt_border_color_hex.setMaxLength(7)
        self.txt_border_color_hex.setPlaceholderText("#000000")
        self.txt_border_color_hex.setFont(QFont("Consolas", 11))
        self.txt_border_color_hex.textChanged.connect(self._on_appearance_hex_changed)
        self._add_control_row(
            layout_colors,
            "Border Color (Hex)",
            self.txt_border_color_hex,
            "Outer outline border drawn around both the collapsed and expanded notch (e.g. #000000 or #00FF7F).",
            extra_controls=[self.swatch_border_preview],
        )

        self.lbl_appearance_error = QLabel("", card_colors)
        self.lbl_appearance_error.setStyleSheet("color: #F38BA8; font-size: 11px;")
        self.lbl_appearance_error.setWordWrap(True)
        self.lbl_appearance_error.hide()
        layout_colors.addWidget(self.lbl_appearance_error)

        app_actions_row = QHBoxLayout()
        app_actions_row.addStretch()
        self.btn_reset_appearance = QPushButton("Reset to Default (#000000)", card_colors)
        self.btn_reset_appearance.setFixedHeight(30)
        self.btn_reset_appearance.setStyleSheet(get_button_stylesheet())
        self.btn_reset_appearance.clicked.connect(self._reset_appearance_defaults)
        app_actions_row.addWidget(self.btn_reset_appearance)
        layout_colors.addLayout(app_actions_row)
        layout_app.addWidget(card_colors)

        card_preview, layout_preview = self._create_setting_card(page_app, "Live Notch Preview")
        preview_stage = QFrame(card_preview)
        preview_stage.setFixedHeight(78)
        preview_stage.setStyleSheet("background-color: #181820; border: 1px dashed #2E2E38; border-radius: 8px;")
        stage_layout = QHBoxLayout(preview_stage)
        stage_layout.setContentsMargins(16, 12, 16, 12)
        stage_layout.addStretch()

        self.appearance_preview_pill = QFrame(preview_stage)
        self.appearance_preview_pill.setFixedSize(250, 38)
        pill_layout = QHBoxLayout(self.appearance_preview_pill)
        pill_layout.setContentsMargins(14, 0, 14, 0)
        pill_layout.setSpacing(8)
        self.appearance_preview_title = QLabel("♪  MediaDock — Now Playing", self.appearance_preview_pill)
        self.appearance_preview_title.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600; background: transparent; border: none;")
        self.appearance_preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill_layout.addWidget(self.appearance_preview_title)

        stage_layout.addWidget(self.appearance_preview_pill)
        stage_layout.addStretch()
        layout_preview.addWidget(preview_stage)
        layout_app.addWidget(card_preview)
        layout_app.addStretch(1)

        self.stacked_widget.addWidget(page_app)

        # Page 4: Audio & Equalizer Settings
        page_aud, layout_aud = self._create_scrollable_page(
            "Audio & Equalizer",
            "Configure visualizer spectrum mode, software/APO boost, tone filters, and 5-band equalizer.",
        )

        # 1. Equalizer APO Status & Master Toggle Card
        card_apo, layout_card_outer = self._create_setting_card(page_aud, "Audio Processing Engine")
        layout_card = QHBoxLayout()
        layout_card.setContentsMargins(0, 0, 0, 0)
        layout_card.setSpacing(12)

        is_apo_installed = self._apo_manager.is_installed()
        if is_apo_installed:
            lbl_apo_status = QLabel("● System-wide audio boost & EQ active (Equalizer APO)", card_apo)
            lbl_apo_status.setStyleSheet("color: #00FF7F; font-size: 11px; font-weight: bold;")
            layout_card.addWidget(lbl_apo_status, 1)
        else:
            lbl_apo_status = QLabel("○ Equalizer APO not detected. Visualizer EQ active.", card_apo)
            lbl_apo_status.setStyleSheet("color: #E0AF68; font-size: 11px;")
            lbl_apo_status.setWordWrap(True)
            btn_install_apo = QPushButton("Install Driver...", card_apo)
            btn_install_apo.setFixedHeight(28)
            btn_install_apo.setStyleSheet(get_button_stylesheet())
            btn_install_apo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(EQUALIZER_APO_DOWNLOAD_URL)))
            layout_card.addWidget(lbl_apo_status, 1)
            layout_card.addWidget(btn_install_apo)

        self.chk_eq_enabled = QCheckBox("Enable EQ & Enhancements", card_apo)
        self.chk_eq_enabled.stateChanged.connect(self._on_audio_control_changed)
        layout_card.addWidget(self.chk_eq_enabled)
        layout_card_outer.addLayout(layout_card)

        self.combo_spectrum_mode = QComboBox(card_apo)
        self.combo_spectrum_mode.setFixedWidth(220)
        self.combo_spectrum_mode.addItem("True FFT Frequency Spectrum", "fft")
        self.combo_spectrum_mode.addItem("Time-Domain RMS Energy", "rms")
        self._add_control_row(
            layout_card_outer,
            "Visualizer Spectrum Mode",
            self.combo_spectrum_mode,
            "Select frequency-bin FFT bars or balanced RMS energy envelope.",
        )
        layout_aud.addWidget(card_apo)

        slider_qss = (
            "QSlider::groove:horizontal { height: 5px; background: #262630; border-radius: 2px; }"
            "QSlider::sub-page:horizontal { background: #00FF7F; border-radius: 2px; }"
            "QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #141414; width: 14px; margin-top: -5px; margin-bottom: -5px; border-radius: 7px; }"
        )

        # 2. Audio Boost (Preamp) Card
        boost_box, boost_l = self._create_setting_card(page_aud, "Audio Boost (Preamp)")

        boost_hdr = QHBoxLayout()
        lbl_preamp_title = QLabel("Gain Level", boost_box)
        lbl_preamp_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()}; font-size: 12px; font-weight: 600;")
        self.lbl_preamp_val = QLabel("+0.0 dB (100%)", boost_box)
        self.lbl_preamp_val.setStyleSheet("color: #00FF7F; font-size: 11px; font-weight: bold;")
        boost_hdr.addWidget(lbl_preamp_title)
        boost_hdr.addStretch()
        boost_hdr.addWidget(self.lbl_preamp_val)
        boost_l.addLayout(boost_hdr)

        self.sld_preamp = QSlider(Qt.Orientation.Horizontal, boost_box)
        self.sld_preamp.setRange(0, 120)  # 0.0 to 12.0 dB
        self.sld_preamp.setValue(0)
        self.sld_preamp.setStyleSheet(slider_qss)
        self.sld_preamp.valueChanged.connect(self._on_audio_control_changed)
        boost_l.addWidget(self.sld_preamp)

        lbl_boost_hint = QLabel("Amplifies audio gain up to +12.0 dB and scales visualizer sensitivity.", boost_box)
        lbl_boost_hint.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        lbl_boost_hint.setWordWrap(True)
        boost_l.addWidget(lbl_boost_hint)
        layout_aud.addWidget(boost_box)

        # 3. Quick Tone Controls Card (Bass, Clarity, Treble, Noise Filter)
        tone_box, tone_l = self._create_setting_card(page_aud, "Tone & Noise Controls")

        grid_tones = QHBoxLayout()
        grid_tones.setSpacing(20)
        # Left column: Bass & Clarity
        col1 = QVBoxLayout()
        col1.setSpacing(8)
        h_bass = QHBoxLayout()
        h_bass.addWidget(QLabel("Bass (Low-Shelf)"))
        self.lbl_bass_val = QLabel("0.0 dB")
        self.lbl_bass_val.setStyleSheet("color: #89B4FA; font-size: 11px; font-weight: 600;")
        h_bass.addStretch()
        h_bass.addWidget(self.lbl_bass_val)
        self.sld_bass = QSlider(Qt.Orientation.Horizontal)
        self.sld_bass.setRange(-120, 120)
        self.sld_bass.setValue(0)
        self.sld_bass.setStyleSheet(slider_qss)
        self.sld_bass.valueChanged.connect(self._on_audio_control_changed)
        col1.addLayout(h_bass)
        col1.addWidget(self.sld_bass)

        h_clarity = QHBoxLayout()
        h_clarity.addWidget(QLabel("Vocal Clarity"))
        self.lbl_clarity_val = QLabel("0.0 dB")
        self.lbl_clarity_val.setStyleSheet("color: #89B4FA; font-size: 11px; font-weight: 600;")
        h_clarity.addStretch()
        h_clarity.addWidget(self.lbl_clarity_val)
        self.sld_clarity = QSlider(Qt.Orientation.Horizontal)
        self.sld_clarity.setRange(-120, 120)
        self.sld_clarity.setValue(0)
        self.sld_clarity.setStyleSheet(slider_qss)
        self.sld_clarity.valueChanged.connect(self._on_audio_control_changed)
        col1.addLayout(h_clarity)
        col1.addWidget(self.sld_clarity)
        grid_tones.addLayout(col1, 1)

        # Right column: Treble & Noise Gate
        col2 = QVBoxLayout()
        col2.setSpacing(8)
        h_treble = QHBoxLayout()
        h_treble.addWidget(QLabel("Treble / Air"))
        self.lbl_treble_val = QLabel("0.0 dB")
        self.lbl_treble_val.setStyleSheet("color: #89B4FA; font-size: 11px; font-weight: 600;")
        h_treble.addStretch()
        h_treble.addWidget(self.lbl_treble_val)
        self.sld_treble = QSlider(Qt.Orientation.Horizontal)
        self.sld_treble.setRange(-120, 120)
        self.sld_treble.setValue(0)
        self.sld_treble.setStyleSheet(slider_qss)
        self.sld_treble.valueChanged.connect(self._on_audio_control_changed)
        col2.addLayout(h_treble)
        col2.addWidget(self.sld_treble)

        h_noise = QHBoxLayout()
        h_noise.addWidget(QLabel("Noise Filter"))
        self.lbl_noise_gate_val = QLabel("5%")
        self.lbl_noise_gate_val.setStyleSheet("color: #89B4FA; font-size: 11px; font-weight: 600;")
        h_noise.addStretch()
        h_noise.addWidget(self.lbl_noise_gate_val)
        self.sld_noise_gate = QSlider(Qt.Orientation.Horizontal)
        self.sld_noise_gate.setRange(0, 50)
        self.sld_noise_gate.setValue(5)
        self.sld_noise_gate.setStyleSheet(slider_qss)
        self.sld_noise_gate.valueChanged.connect(self._on_audio_control_changed)
        col2.addLayout(h_noise)
        col2.addWidget(self.sld_noise_gate)
        grid_tones.addLayout(col2, 1)

        tone_l.addLayout(grid_tones)
        layout_aud.addWidget(tone_box)

        # 4. 5-Band Equalizer Card
        eq_box, eq_l = self._create_setting_card(page_aud, "5-Band Equalizer")

        eq_hdr = QHBoxLayout()
        lbl_eq_sub = QLabel("Preset Profile", eq_box)
        lbl_eq_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        eq_hdr.addWidget(lbl_eq_sub)
        eq_hdr.addStretch()

        self.cmb_preset = QComboBox(eq_box)
        self.cmb_preset.setFixedWidth(150)
        self.cmb_preset.addItems(["Flat", "Bass Boost", "Vocal Clarity", "Electronic", "Rock", "Acoustic", "Custom"])
        self.cmb_preset.currentTextChanged.connect(self._on_preset_changed)
        eq_hdr.addWidget(self.cmb_preset)

        self.btn_reset_eq = QPushButton("Reset Flat", eq_box)
        self.btn_reset_eq.setFixedHeight(30)
        self.btn_reset_eq.setStyleSheet(get_button_stylesheet())
        self.btn_reset_eq.clicked.connect(self._reset_eq_flat)
        eq_hdr.addWidget(self.btn_reset_eq)
        eq_l.addLayout(eq_hdr)

        # 5 Spacious Equalizer Sliders
        eq_bands_layout = QHBoxLayout()
        eq_bands_layout.setContentsMargins(8, 6, 8, 2)
        eq_bands_layout.setSpacing(14)

        self.eq_band_sliders: List[QSlider] = []
        self.eq_band_labels: List[QLabel] = []
        freq_names = ["60 Hz", "250 Hz", "1 kHz", "4 kHz", "16 kHz"]

        for name in freq_names:
            band_col = QVBoxLayout()
            band_col.setSpacing(6)
            lbl_freq = QLabel(name)
            lbl_freq.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()}; font-size: 11px; font-weight: 600;")
            lbl_freq.setAlignment(Qt.AlignmentFlag.AlignCenter)

            sld = QSlider(Qt.Orientation.Vertical)
            sld.setFixedHeight(96)
            sld.setRange(-120, 120)
            sld.setValue(0)
            sld.setStyleSheet(
                "QSlider::groove:vertical { width: 5px; background: #262630; border-radius: 2px; }"
                "QSlider::sub-page:vertical { background: #262630; border-radius: 2px; }"
                "QSlider::add-page:vertical { background: #00FF7F; border-radius: 2px; }"
                "QSlider::handle:vertical { background: #FFFFFF; border: 1px solid #141414; height: 14px; margin-left: -5px; margin-right: -5px; border-radius: 7px; }"
            )
            sld.valueChanged.connect(self._on_band_slider_changed)

            lbl_v = QLabel("0.0")
            lbl_v.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 10px;")
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)

            band_col.addWidget(lbl_freq)
            band_col.addWidget(sld, 0, Qt.AlignmentFlag.AlignCenter)
            band_col.addWidget(lbl_v)
            eq_bands_layout.addLayout(band_col, 1)

            self.eq_band_sliders.append(sld)
            self.eq_band_labels.append(lbl_v)

        self.sld_band_60 = self.eq_band_sliders[0]
        self.sld_band_250 = self.eq_band_sliders[1]
        self.sld_band_1000 = self.eq_band_sliders[2]
        self.sld_band_4000 = self.eq_band_sliders[3]
        self.sld_band_16000 = self.eq_band_sliders[4]

        eq_l.addLayout(eq_bands_layout)
        layout_aud.addWidget(eq_box)
        layout_aud.addStretch(1)

        self.stacked_widget.addWidget(page_aud)

        # Page 5: About Page
        page_about, layout_about = self._create_scrollable_page(
            "About MediaDock",
            "Version information, open-source repository link, runtime stack, and quick reference.",
        )

        card_identity, layout_identity = self._create_setting_card(page_about)
        hdr_about = QHBoxLayout()
        lbl_about_title = QLabel("MediaDock", card_identity)
        lbl_about_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_about_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        hdr_about.addWidget(lbl_about_title)

        lbl_ver = QLabel("Version 1.0.0-rc1", card_identity)
        lbl_ver.setStyleSheet(
            "background-color: #1A2421; color: #00FF7F; border: 1px solid #264A3B; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: bold;"
        )
        hdr_about.addWidget(lbl_ver)
        hdr_about.addStretch()
        layout_identity.addLayout(hdr_about)

        lbl_desc = QLabel(
            "Native Windows top-notch Dynamic Island media controller built with Python, PySide6 (Qt), and WinRT GSMTC.\n"
            "Includes instant media detection across Spotify, browsers, and desktop players, live synchronized lyrics, "
            "real-time audio spectrum visualization, Equalizer APO tone controls, and global keyboard shortcuts.",
            card_identity,
        )
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; line-height: 1.45;")
        lbl_desc.setWordWrap(True)
        layout_identity.addWidget(lbl_desc)
        layout_about.addWidget(card_identity)

        card_repo, layout_repo = self._create_setting_card(page_about, "Project & GitHub Repository")
        self.lbl_github_link = QLabel(
            f'Repository: <a href="{GITHUB_REPO_URL}" style="color: #00FF7F; text-decoration: none;">{GITHUB_REPO_URL}</a>',
            card_repo,
        )
        self.lbl_github_link.setOpenExternalLinks(True)
        self.lbl_github_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.lbl_github_link.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()}; font-size: 12px;")
        layout_repo.addWidget(self.lbl_github_link)

        repo_btn_row = QHBoxLayout()
        repo_btn_row.setSpacing(10)
        self.btn_open_github = QPushButton("Open GitHub Repository", card_repo)
        self.btn_open_github.setFixedHeight(32)
        self.btn_open_github.setStyleSheet(get_button_stylesheet())
        self.btn_open_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL)))

        self.btn_report_issue = QPushButton("Report an Issue", card_repo)
        self.btn_report_issue.setFixedHeight(32)
        self.btn_report_issue.setStyleSheet(get_button_stylesheet())
        self.btn_report_issue.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_ISSUES_URL)))

        repo_btn_row.addWidget(self.btn_open_github)
        repo_btn_row.addWidget(self.btn_report_issue)
        repo_btn_row.addStretch()
        layout_repo.addLayout(repo_btn_row)
        layout_about.addWidget(card_repo)

        card_env, layout_env = self._create_setting_card(page_about, "Controls & Runtime Details")
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        lbl_env = QLabel(
            "• Expand / Collapse: Hover or click the top notch bar (configurable in Dynamic Island).\n"
            "• Quick Context Menu: Right-click the notch for Settings, Pin, or Hide options.\n"
            f"• Runtime Stack: Python {py_ver}  |  Qt {QT_RUNTIME_VERSION} (PySide6)  |  Windows GSMTC & Core Audio",
            card_env,
        )
        lbl_env.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; line-height: 1.5;")
        lbl_env.setWordWrap(True)
        layout_env.addWidget(lbl_env)
        layout_about.addWidget(card_env)
        layout_about.addStretch(1)

        self.stacked_widget.addWidget(page_about)

        right_layout.addWidget(self.stacked_widget, 1)

        # Connect Sidebar to StackedWidget
        self.sidebar.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        # Bottom Button Bar (Cancel / Save)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        btn_style = get_button_stylesheet()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setFixedSize(92, 32)
        self.btn_cancel.setStyleSheet(
            "QPushButton {"
            "  background-color: rgba(255, 255, 255, 0.08);"
            "  color: #FFFFFF;"
            "  border: 1px solid rgba(255, 255, 255, 0.14);"
            "  border-radius: 7px;"
            "  font-weight: 600;"
            "  font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "  background-color: rgba(255, 255, 255, 0.14);"
            "}"
            "QPushButton:pressed {"
            "  background-color: rgba(255, 255, 255, 0.05);"
            "}"
        )
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save", self)
        self.btn_save.setFixedSize(92, 32)
        self.btn_save.setStyleSheet(
            "QPushButton {"
            "  background-color: rgba(0, 255, 127, 0.16);"
            "  color: #00FF7F;"
            "  border: 1px solid rgba(0, 255, 127, 0.42);"
            "  border-radius: 7px;"
            "  font-weight: bold;"
            "  font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "  background-color: rgba(0, 255, 127, 0.26);"
            "}"
            "QPushButton:pressed {"
            "  background-color: rgba(0, 255, 127, 0.12);"
            "}"
        )
        self.btn_save.clicked.connect(self.save_settings)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)

        right_layout.addLayout(btn_layout)
        root_layout.addWidget(right_container, 1)

    @property
    def txt_hotkey_show_hide(self) -> ShortcutRecorderWidget:
        """Backward compatibility property wrapper."""
        return self.rec_hotkey_show_hide

    @property
    def txt_hotkey_play_pause(self) -> ShortcutRecorderWidget:
        """Backward compatibility property wrapper."""
        return self.rec_hotkey_play_pause

    def showEvent(self, event) -> None:
        """Refresh preference controls and reapply hardware Gaussian blur backdrop on show."""
        super().showEvent(event)
        self._apply_gaussian_blur_backdrop()
        self.load_settings()

    def _on_audio_control_changed(self) -> None:
        """Handle audio slider changes, update labels, and update visualizer live."""
        preamp_db = self.sld_preamp.value() / 10.0
        pct = int(round(math.pow(10.0, preamp_db / 20.0) * 100))
        self.lbl_preamp_val.setText(f"+{preamp_db:.1f} dB ({pct}%)")

        bass_db = self.sld_bass.value() / 10.0
        self.lbl_bass_val.setText(f"{bass_db:+.1f} dB")

        clarity_db = self.sld_clarity.value() / 10.0
        self.lbl_clarity_val.setText(f"{clarity_db:+.1f} dB")

        treble_db = self.sld_treble.value() / 10.0
        self.lbl_treble_val.setText(f"{treble_db:+.1f} dB")

        noise_gate = self.sld_noise_gate.value()
        self.lbl_noise_gate_val.setText(f"{noise_gate}%")

        for sld, lbl in zip(self.eq_band_sliders, self.eq_band_labels):
            lbl.setText(f"{sld.value() / 10.0:+.1f}")

        # Update visualizer live if media_core is available
        if not self._is_updating_ui and self._media_core and hasattr(self._media_core, "_analyzer") and self._media_core._analyzer:
            bands = [s.value() / 10.0 for s in self.eq_band_sliders]
            self._media_core._analyzer.set_eq_profile(
                preamp_boost_db=preamp_db,
                bass_db=bass_db,
                clarity_db=clarity_db,
                treble_db=treble_db,
                eq_bands=bands,
                noise_gate_percent=noise_gate,
                eq_enabled=self.chk_eq_enabled.isChecked(),
            )

    def _on_band_slider_changed(self) -> None:
        """Handle individual EQ band changes and flag Custom preset."""
        if not self._is_updating_ui:
            self.cmb_preset.blockSignals(True)
            self.cmb_preset.setCurrentText("Custom")
            self.cmb_preset.blockSignals(False)
        self._on_audio_control_changed()

    def _on_preset_changed(self, preset_name: str) -> None:
        """Apply selected preset to the 5 equalizer bands."""
        if preset_name in EQ_PRESETS:
            self._is_updating_ui = True
            bands = EQ_PRESETS[preset_name]
            for sld, val in zip(self.eq_band_sliders, bands):
                sld.setValue(int(round(val * 10)))
            self._is_updating_ui = False
            self._on_audio_control_changed()

    def _reset_eq_flat(self) -> None:
        """Reset equalizer and tone sliders to flat 0 dB."""
        self._is_updating_ui = True
        self.sld_preamp.setValue(0)
        self.sld_bass.setValue(0)
        self.sld_clarity.setValue(0)
        self.sld_treble.setValue(0)
        self.sld_noise_gate.setValue(5)
        for sld in self.eq_band_sliders:
            sld.setValue(0)
        self.cmb_preset.setCurrentText("Flat")
        self._is_updating_ui = False
        self._on_audio_control_changed()

    def _on_appearance_hex_changed(self) -> None:
        """Update hex swatch previews live while typing."""
        if not self._is_updating_ui:
            self._update_appearance_preview()

    def _reset_appearance_defaults(self) -> None:
        """Reset appearance hex fields back to #000000 defaults."""
        self._is_updating_ui = True
        self.txt_bg_color_hex.setText("#000000")
        self.txt_border_color_hex.setText("#000000")
        self.lbl_appearance_error.hide()
        self._is_updating_ui = False
        self._update_appearance_preview()

    def _update_appearance_preview(self) -> None:
        """Refresh color swatches and live notch preview pill from hex fields."""
        bg_hex = parse_hex_color(self.txt_bg_color_hex.text())
        border_hex = parse_hex_color(self.txt_border_color_hex.text())

        bg_display = bg_hex if bg_hex else "#000000"
        border_display = border_hex if border_hex else "#000000"

        self.swatch_bg_preview.setStyleSheet(
            f"background-color: {bg_display}; border-radius: 7px; border: 1px solid {'#3C3C48' if bg_hex else '#C1121C'};"
        )
        self.swatch_border_preview.setStyleSheet(
            f"background-color: {border_display}; border-radius: 7px; border: 1px solid {'#3C3C48' if border_hex else '#C1121C'};"
        )

        pill_border = border_display if border_display != "#000000" else "#2E2E36"
        self.appearance_preview_pill.setStyleSheet(
            f"background-color: {bg_display}; border: 1.5px solid {pill_border}; border-radius: 16px;"
        )
        # Contrast hint so light backgrounds keep readable text in preview
        bg_qcolor = QColor(bg_display)
        txt_color = "#111115" if bg_qcolor.lightness() > 165 else "#FFFFFF"
        self.appearance_preview_title.setStyleSheet(
            f"color: {txt_color}; font-size: 11px; font-weight: 600; background: transparent; border: none;"
        )

    def load_settings(self) -> None:
        """Load current preference values from SettingsManager into controls."""
        self.chk_close_to_tray.setChecked(self._settings_manager.get_close_to_tray())
        self.chk_start_hidden.setChecked(self._settings_manager.get_start_hidden())
        self.chk_autostart_windows.setChecked(
            self._settings_manager.get_autostart_windows()
        )
        self.chk_always_on_top.setChecked(self._settings_manager.get_always_on_top())
        self.chk_dynamic_island.setChecked(
            self._settings_manager.get_dynamic_island_enabled()
        )
        self.chk_fullscreen_auto_hide.setChecked(
            self._settings_manager.get_fullscreen_auto_hide()
        )
        self.chk_lyrics_enabled.setChecked(
            self._settings_manager.get_lyrics_enabled()
        )
        mon_idx = self.combo_display_monitor.findData(self._settings_manager.get_display_monitor())
        if mon_idx >= 0:
            self.combo_display_monitor.setCurrentIndex(mon_idx)

        trig_idx = self.combo_expand_trigger.findData(self._settings_manager.get_expand_trigger())
        if trig_idx >= 0:
            self.combo_expand_trigger.setCurrentIndex(trig_idx)
        self.spn_hover_intent.setValue(self._settings_manager.get_hover_intent_delay_ms())

        self.spn_collapse_delay.setValue(
            self._settings_manager.get_collapse_delay_ms()
        )

        self.rec_hotkey_show_hide.set_sequence(
            self._settings_manager.get_hotkey_show_hide()
        )
        self.rec_hotkey_play_pause.set_sequence(
            self._settings_manager.get_hotkey_play_pause()
        )

        # Appearance Hex Colors & Audio Settings
        self._is_updating_ui = True
        self.txt_bg_color_hex.setText(self._settings_manager.get_notch_bg_color())
        self.txt_border_color_hex.setText(self._settings_manager.get_notch_border_color())
        self.lbl_appearance_error.hide()

        self.chk_eq_enabled.setChecked(self._settings_manager.get_eq_enabled())
        self.sld_preamp.setValue(int(round(self._settings_manager.get_preamp_boost_db() * 10)))
        self.sld_bass.setValue(int(round(self._settings_manager.get_bass_db() * 10)))
        self.sld_clarity.setValue(int(round(self._settings_manager.get_clarity_db() * 10)))
        self.sld_treble.setValue(int(round(self._settings_manager.get_treble_db() * 10)))
        self.sld_noise_gate.setValue(self._settings_manager.get_noise_gate_percent())

        preset = self._settings_manager.get_eq_preset()
        self.cmb_preset.blockSignals(True)
        self.cmb_preset.setCurrentText(preset if preset else "Flat")
        self.cmb_preset.blockSignals(False)

        bands = self._settings_manager.get_eq_bands()
        for i, sld in enumerate(self.eq_band_sliders):
            v = bands[i] if i < len(bands) else 0.0
            sld.setValue(int(round(v * 10)))

        spec_idx = self.combo_spectrum_mode.findData(self._settings_manager.get_spectrum_mode())
        if spec_idx >= 0:
            self.combo_spectrum_mode.setCurrentIndex(spec_idx)

        self._is_updating_ui = False
        self._update_appearance_preview()
        self._on_audio_control_changed()

        self.lbl_error.hide()

    def save_settings(self) -> None:
        """Validate appearance hex codes & hotkeys, persist values, and apply updates."""
        # 1. Validate Appearance hex color inputs
        bg_hex = parse_hex_color(self.txt_bg_color_hex.text())
        border_hex = parse_hex_color(self.txt_border_color_hex.text())
        if bg_hex is None or border_hex is None:
            self.lbl_appearance_error.setText(
                "Please enter valid 6-digit hex color codes (e.g. #000000) for Background and Border."
            )
            self.lbl_appearance_error.show()
            self.sidebar.setCurrentRow(3)  # Switch to Appearance page
            return

        self.lbl_appearance_error.hide()
        self._is_updating_ui = True
        self.txt_bg_color_hex.setText(bg_hex)
        self.txt_border_color_hex.setText(border_hex)
        self._is_updating_ui = False
        self._update_appearance_preview()

        # 2. Persist validated general, dynamic island, appearance, and audio settings
        self._settings_manager.set_close_to_tray(self.chk_close_to_tray.isChecked())
        self._settings_manager.set_start_hidden(self.chk_start_hidden.isChecked())
        self._settings_manager.set_autostart_windows(
            self.chk_autostart_windows.isChecked()
        )
        self._settings_manager.set_always_on_top(self.chk_always_on_top.isChecked())
        self._settings_manager.set_dynamic_island_enabled(
            self.chk_dynamic_island.isChecked()
        )
        self._settings_manager.set_collapse_delay_ms(self.spn_collapse_delay.value())
        self._settings_manager.set_fullscreen_auto_hide(
            self.chk_fullscreen_auto_hide.isChecked()
        )
        self._settings_manager.set_lyrics_enabled(
            self.chk_lyrics_enabled.isChecked()
        )
        self._settings_manager.set_display_monitor(
            str(self.combo_display_monitor.currentData() or "primary")
        )
        self._settings_manager.set_expand_trigger(
            str(self.combo_expand_trigger.currentData() or "hover")
        )
        self._settings_manager.set_hover_intent_delay_ms(
            self.spn_hover_intent.value()
        )
        self._settings_manager.set_notch_bg_color(bg_hex)
        self._settings_manager.set_notch_border_color(border_hex)
        self._settings_manager.set_spectrum_mode(
            str(self.combo_spectrum_mode.currentData() or "fft")
        )

        # Save Audio & Equalizer Settings
        self._settings_manager.set_eq_enabled(self.chk_eq_enabled.isChecked())
        self._settings_manager.set_preamp_boost_db(self.sld_preamp.value() / 10.0)
        self._settings_manager.set_bass_db(self.sld_bass.value() / 10.0)
        self._settings_manager.set_clarity_db(self.sld_clarity.value() / 10.0)
        self._settings_manager.set_treble_db(self.sld_treble.value() / 10.0)
        self._settings_manager.set_noise_gate_percent(self.sld_noise_gate.value())
        self._settings_manager.set_eq_preset(self.cmb_preset.currentText())

        bands = [sld.value() / 10.0 for sld in self.eq_band_sliders]
        self._settings_manager.set_eq_bands(bands)

        if self._media_core and hasattr(self._media_core, "sync_audio_settings"):
            self._media_core.sync_audio_settings(self._settings_manager)

        # 2. Validate hotkey inputs
        if self.rec_hotkey_show_hide.validation_error():
            self.lbl_error.setText(self.rec_hotkey_show_hide.validation_error())
            self.lbl_error.show()
            self.sidebar.setCurrentRow(1)  # Switch to Global Shortcuts page
            return

        if self.rec_hotkey_play_pause.validation_error():
            self.lbl_error.setText(self.rec_hotkey_play_pause.validation_error())
            self.lbl_error.show()
            self.sidebar.setCurrentRow(1)  # Switch to Global Shortcuts page
            return

        sh_val = self.rec_hotkey_show_hide.sequence().strip()
        pp_val = self.rec_hotkey_play_pause.sequence().strip()

        # 3. Check duplicate shortcuts
        if sh_val and pp_val and sh_val == pp_val:
            self.lbl_error.setText("Show/Hide and Play/Pause cannot use the same shortcut.")
            self.lbl_error.show()
            self.sidebar.setCurrentRow(1)  # Switch to Global Shortcuts page
            return

        cur_sh = self._settings_manager.get_hotkey_show_hide()
        cur_pp = self._settings_manager.get_hotkey_play_pause()

        # 4. Only attempt hotkey rebind if hotkey sequence strings actually changed
        if (sh_val != cur_sh or pp_val != cur_pp) and self._hotkey_manager and hasattr(self._hotkey_manager, "rebind_hotkeys"):
            success = self._hotkey_manager.rebind_hotkeys(sh_val, pp_val)
            if not success:
                self.lbl_error.setText(
                    "Failed to register global hotkeys with Windows. Shortcut combination may be duplicate, invalid, or already in use by another application."
                )
                self.lbl_error.show()
                self.sidebar.setCurrentRow(1)  # Switch to Global Shortcuts page
                return

        self.lbl_error.hide()

        if sh_val != cur_sh or pp_val != cur_pp:
            self._settings_manager.set_hotkey_show_hide(sh_val)
            self._settings_manager.set_hotkey_play_pause(pp_val)

        self._settings_manager.sync()
        self.accept()
