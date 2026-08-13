from typing import Optional, Any
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent, QColor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QPushButton,
    QWidget,
    QFrame,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
)

from src.core.settings import SettingsManager
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
    """Landscape Preferences dialog with persistent left navigation sidebar and QStackedWidget page architecture."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        hotkey_manager: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._settings_manager = settings_manager
        self._hotkey_manager = hotkey_manager

        self.setWindowTitle("MediaDock Preferences")
        self.setFixedSize(680, 440)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self._init_ui()
        self.load_settings()

    def _init_ui(self) -> None:
        """Initialize landscape sidebar and stacked pages layout."""
        self.setStyleSheet(f"QDialog {{ background-color: {COLOR_BG_BASE.name()}; }}")

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # 1. Persistent Left Navigation Sidebar (160px)
        self.sidebar = QListWidget(self)
        self.sidebar.setFixedWidth(160)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.setStyleSheet(
            "QListWidget {"
            f"  background-color: {COLOR_BG_MANTLE.name()};"
            f"  border: 1px solid {COLOR_BORDER.name()};"
            "  border-radius: 8px;"
            "  padding: 6px;"
            f"  color: {COLOR_TEXT_PRIMARY.name()};"
            "  font-family: 'Segoe UI', sans-serif;"
            "  font-size: 12px;"
            "  outline: 0;"
            "}"
            "QListWidget::item {"
            "  height: 36px;"
            "  padding-left: 12px;"
            "  border-radius: 6px;"
            "  margin-bottom: 3px;"
            "  border: none;"
            "}"
            "QListWidget::item:selected {"
            f"  background-color: {COLOR_BG_SURFACE.name()};"
            "  color: #FFFFFF;"
            "  font-weight: bold;"
            f"  border-left: 3px solid {COLOR_ACCENT_GREEN.name()};"
            "}"
            "QListWidget::item:hover:!selected {"
            f"  background-color: {COLOR_BG_BASE.name()};"
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
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(10)

        # QStackedWidget for Page switching
        self.stacked_widget = QStackedWidget(right_container)

        # Page 0: General Preferences
        page_prefs = QWidget()
        layout_prefs = QVBoxLayout(page_prefs)
        layout_prefs.setContentsMargins(0, 0, 0, 0)
        layout_prefs.setSpacing(10)

        lbl_prefs_title = QLabel("General Preferences", page_prefs)
        lbl_prefs_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_prefs_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        layout_prefs.addWidget(lbl_prefs_title)

        line_p = QFrame(page_prefs)
        line_p.setFrameShape(QFrame.Shape.HLine)
        line_p.setFrameShadow(QFrame.Shadow.Sunken)
        line_p.setStyleSheet(f"color: {COLOR_BORDER.name()};")
        layout_prefs.addWidget(line_p)

        self.chk_close_to_tray = QCheckBox("Close to System Tray", page_prefs)
        self.lbl_close_to_tray_desc = QLabel("Closing main window hides to tray instead of quitting process", page_prefs)
        self.lbl_close_to_tray_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;")

        self.chk_start_hidden = QCheckBox("Start Minimized to Tray", page_prefs)
        self.lbl_start_hidden_desc = QLabel("Application starts silently in system tray without opening window", page_prefs)
        self.lbl_start_hidden_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;")

        self.chk_autostart_windows = QCheckBox("Start with Windows", page_prefs)
        self.lbl_autostart_windows_desc = QLabel("Automatically launch MediaDock when you log into Windows", page_prefs)
        self.lbl_autostart_windows_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;")

        self.chk_always_on_top = QCheckBox("Always On Top", page_prefs)
        self.lbl_always_on_top_desc = QLabel("Keep window floating above other application windows", page_prefs)
        self.lbl_always_on_top_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;")

        self.chk_dynamic_island = QCheckBox("Enable Dynamic Island", page_prefs)
        self.lbl_dynamic_island_desc = QLabel("Anchors ambient capsule to top-center of primary screen", page_prefs)
        self.lbl_dynamic_island_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;")

        layout_prefs.addWidget(self.chk_close_to_tray)
        layout_prefs.addWidget(self.lbl_close_to_tray_desc)
        layout_prefs.addWidget(self.chk_start_hidden)
        layout_prefs.addWidget(self.lbl_start_hidden_desc)
        layout_prefs.addWidget(self.chk_autostart_windows)
        layout_prefs.addWidget(self.lbl_autostart_windows_desc)
        layout_prefs.addWidget(self.chk_always_on_top)
        layout_prefs.addWidget(self.lbl_always_on_top_desc)
        layout_prefs.addWidget(self.chk_dynamic_island)
        layout_prefs.addWidget(self.lbl_dynamic_island_desc)
        layout_prefs.addStretch()

        self.stacked_widget.addWidget(page_prefs)

        # Page 1: Global Shortcuts
        page_hk = QWidget()
        layout_hk = QVBoxLayout(page_hk)
        layout_hk.setContentsMargins(0, 0, 0, 0)
        layout_hk.setSpacing(10)

        lbl_hk_title = QLabel("Global Shortcuts", page_hk)
        lbl_hk_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_hk_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        layout_hk.addWidget(lbl_hk_title)

        lbl_hk_sub = QLabel("Configure OS-wide shortcuts (strictly 2 or 3 keys required)", page_hk)
        lbl_hk_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        layout_hk.addWidget(lbl_hk_sub)

        line_hk = QFrame(page_hk)
        line_hk.setFrameShape(QFrame.Shape.HLine)
        line_hk.setFrameShadow(QFrame.Shadow.Sunken)
        line_hk.setStyleSheet(f"color: {COLOR_BORDER.name()};")
        layout_hk.addWidget(line_hk)

        hk_sh_layout = QHBoxLayout()
        lbl_hk_sh = QLabel("Show / Hide:", page_hk)
        lbl_hk_sh.setFixedWidth(90)
        self.rec_hotkey_show_hide = ShortcutRecorderWidget("Ctrl+Alt+S", page_hk)
        hk_sh_layout.addWidget(lbl_hk_sh)
        hk_sh_layout.addWidget(self.rec_hotkey_show_hide)
        layout_hk.addLayout(hk_sh_layout)

        hk_pp_layout = QHBoxLayout()
        lbl_hk_pp = QLabel("Play / Pause:", page_hk)
        lbl_hk_pp.setFixedWidth(90)
        self.rec_hotkey_play_pause = ShortcutRecorderWidget("Ctrl+Alt+Space", page_hk)
        hk_pp_layout.addWidget(lbl_hk_pp)
        hk_pp_layout.addWidget(self.rec_hotkey_play_pause)
        layout_hk.addLayout(hk_pp_layout)

        self.lbl_error = QLabel("", page_hk)
        self.lbl_error.setStyleSheet("color: #F38BA8; font-size: 11px;")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        layout_hk.addWidget(self.lbl_error)
        layout_hk.addStretch()

        self.stacked_widget.addWidget(page_hk)

        # Page 2: Dynamic Island Settings
        page_di = QWidget()
        layout_di = QVBoxLayout(page_di)
        layout_di.setContentsMargins(0, 0, 0, 0)
        layout_di.setSpacing(10)

        lbl_di_title = QLabel("Dynamic Island Settings", page_di)
        lbl_di_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_di_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        layout_di.addWidget(lbl_di_title)

        line_di = QFrame(page_di)
        line_di.setFrameShape(QFrame.Shape.HLine)
        line_di.setFrameShadow(QFrame.Shadow.Sunken)
        line_di.setStyleSheet(f"color: {COLOR_BORDER.name()};")
        layout_di.addWidget(line_di)

        delay_layout = QHBoxLayout()
        lbl_delay = QLabel("Collapse Delay:", page_di)
        lbl_delay.setStyleSheet("font-size: 12px;")
        self.spn_collapse_delay = CollapseDelaySpinBox(page_di)
        delay_layout.addWidget(lbl_delay)
        delay_layout.addWidget(self.spn_collapse_delay)
        delay_layout.addStretch()
        layout_di.addLayout(delay_layout)

        lbl_delay_desc = QLabel(
            "Time in milliseconds before the expanded media card auto-collapses to the capsule upon mouse leave.", page_di
        )
        lbl_delay_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        lbl_delay_desc.setWordWrap(True)
        layout_di.addWidget(lbl_delay_desc)
        layout_di.addStretch()

        self.stacked_widget.addWidget(page_di)

        # Page 3: Appearance Baseline
        page_app = QWidget()
        layout_app = QVBoxLayout(page_app)
        layout_app.setContentsMargins(0, 0, 0, 0)
        layout_app.setSpacing(10)

        lbl_app_title = QLabel("Appearance", page_app)
        lbl_app_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_app_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        layout_app.addWidget(lbl_app_title)

        line_app = QFrame(page_app)
        line_app.setFrameShape(QFrame.Shape.HLine)
        line_app.setFrameShadow(QFrame.Shadow.Sunken)
        line_app.setStyleSheet(f"color: {COLOR_BORDER.name()};")
        layout_app.addWidget(line_app)

        lbl_app_info = QLabel(
            "MediaDock System Visual Identity (Fixed Product Baseline):\n"
            "Dynamic Island background (#000000), border (#000000), and status indicators (Active #00FF7F, Inactive #C1121C) are fixed by product identity and are non-customizable.",
            page_app,
        )
        lbl_app_info.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        lbl_app_info.setWordWrap(True)
        layout_app.addWidget(lbl_app_info)

        # Fixed System Color Badges
        color_grid = QHBoxLayout()
        colors = [
            ("Background", "#000000"),
            ("Border", "#000000"),
            ("Active Status", "#00FF7F"),
            ("Inactive Status", "#C1121C"),
        ]
        for label, hex_code in colors:
            badge = QWidget(page_app)
            badge_l = QVBoxLayout(badge)
            badge_l.setContentsMargins(6, 6, 6, 6)
            swatch = QLabel(badge)
            swatch.setFixedSize(36, 22)
            swatch.setStyleSheet(f"background-color: {hex_code}; border-radius: 4px; border: 1px solid #2A2A2A;")
            lbl_c = QLabel(label, badge)
            lbl_c.setStyleSheet("font-size: 10px; color: #FFFFFF;")
            badge_l.addWidget(swatch, 0, Qt.AlignmentFlag.AlignCenter)
            badge_l.addWidget(lbl_c, 0, Qt.AlignmentFlag.AlignCenter)
            color_grid.addWidget(badge)
        color_grid.addStretch()
        layout_app.addLayout(color_grid)
        layout_app.addStretch()

        self.stacked_widget.addWidget(page_app)

        # Page 4: Audio Baseline
        page_aud = QWidget()
        layout_aud = QVBoxLayout(page_aud)
        layout_aud.setContentsMargins(0, 0, 0, 0)
        layout_aud.setSpacing(10)

        lbl_aud_title = QLabel("Audio Settings", page_aud)
        lbl_aud_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_aud_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        layout_aud.addWidget(lbl_aud_title)

        line_aud = QFrame(page_aud)
        line_aud.setFrameShape(QFrame.Shape.HLine)
        line_aud.setFrameShadow(QFrame.Shadow.Sunken)
        line_aud.setStyleSheet(f"color: {COLOR_BORDER.name()};")
        layout_aud.addWidget(line_aud)

        lbl_aud_info = QLabel("Audio provider and master volume control integration.", page_aud)
        lbl_aud_info.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        layout_aud.addWidget(lbl_aud_info)
        layout_aud.addStretch()

        self.stacked_widget.addWidget(page_aud)

        # Page 5: About Page
        page_about = QWidget()
        layout_about = QVBoxLayout(page_about)
        layout_about.setContentsMargins(0, 0, 0, 0)
        layout_about.setSpacing(8)

        lbl_about_title = QLabel("MediaDock", page_about)
        lbl_about_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_about_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        layout_about.addWidget(lbl_about_title)

        lbl_ver = QLabel("Version 1.0.0-rc1", page_about)
        lbl_ver.setStyleSheet("color: #89B4FA; font-size: 11px; font-weight: bold;")
        layout_about.addWidget(lbl_ver)

        line_about = QFrame(page_about)
        line_about.setFrameShape(QFrame.Shape.HLine)
        line_about.setFrameShadow(QFrame.Shadow.Sunken)
        line_about.setStyleSheet(f"color: {COLOR_BORDER.name()};")
        layout_about.addWidget(line_about)

        lbl_desc = QLabel(
            "Native Windows desktop media application built with Python 3.14, PySide6 (Qt for Python), and PyWinRT.\n\n"
            "Features top-center Dynamic Island overlay, Windows GSMTC media session detection, and master volume control.",
            page_about,
        )
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        layout_about.addWidget(lbl_desc)
        layout_about.addStretch()

        self.stacked_widget.addWidget(page_about)

        right_layout.addWidget(self.stacked_widget)

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
        self.btn_cancel.setFixedSize(80, 28)
        self.btn_cancel.setStyleSheet(btn_style)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save", self)
        self.btn_save.setFixedSize(80, 28)
        self.btn_save.setStyleSheet(btn_style)
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
        """Refresh preference controls from SettingsManager upon show event."""
        super().showEvent(event)
        self.load_settings()

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

        self.spn_collapse_delay.setValue(
            self._settings_manager.get_collapse_delay_ms()
        )

        self.rec_hotkey_show_hide.set_sequence(
            self._settings_manager.get_hotkey_show_hide()
        )
        self.rec_hotkey_play_pause.set_sequence(
            self._settings_manager.get_hotkey_play_pause()
        )
        self.lbl_error.hide()

    def save_settings(self) -> None:
        """Save dialog values to SettingsManager and attempt hotkey rebind."""
        # 1. ALWAYS save general preferences regardless of hotkey validation
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
