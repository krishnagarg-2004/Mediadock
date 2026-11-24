import math
from typing import Optional, Any, Dict, List
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QFont, QKeyEvent, QColor, QDesktopServices
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
    QSlider,
    QComboBox,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
)

from src.core.settings import SettingsManager
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
    """Landscape Preferences dialog with persistent left navigation sidebar and QStackedWidget page architecture."""

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

        self.chk_dynamic_island = QCheckBox("Enable Dynamic Island (Top Notch)", page_prefs)
        self.lbl_dynamic_island_desc = QLabel("Anchors ambient notch screen to top-center of selected screen", page_prefs)
        self.lbl_dynamic_island_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;")

        self.chk_fullscreen_auto_hide = QCheckBox("Auto-Hide in Fullscreen Games & Apps", page_prefs)
        self.lbl_fullscreen_auto_hide_desc = QLabel("Suppresses top notch overlay when playing games or watching fullscreen videos", page_prefs)
        self.lbl_fullscreen_auto_hide_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;")

        self.chk_lyrics_enabled = QCheckBox("Enable Live Synchronized Lyrics", page_prefs)
        self.lbl_lyrics_desc = QLabel("Displays synchronized lyric lines in expanded media card when available", page_prefs)
        self.lbl_lyrics_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;")

        mon_layout = QHBoxLayout()
        mon_layout.setContentsMargins(24, 4, 0, 0)
        lbl_mon = QLabel("Target Display Monitor:", page_prefs)
        lbl_mon.setStyleSheet("font-size: 12px;")
        self.combo_display_monitor = QComboBox(page_prefs)
        self.combo_display_monitor.setFixedWidth(160)
        self.combo_display_monitor.addItem("Primary Monitor", "primary")
        from PySide6.QtGui import QGuiApplication
        screens = QGuiApplication.screens()
        for idx, scr in enumerate(screens):
            self.combo_display_monitor.addItem(f"Monitor {idx + 1} ({scr.name()})", scr.name())
        mon_layout.addWidget(lbl_mon)
        mon_layout.addWidget(self.combo_display_monitor)
        mon_layout.addStretch()

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
        layout_prefs.addWidget(self.chk_fullscreen_auto_hide)
        layout_prefs.addWidget(self.lbl_fullscreen_auto_hide_desc)
        layout_prefs.addWidget(self.chk_lyrics_enabled)
        layout_prefs.addWidget(self.lbl_lyrics_desc)
        layout_prefs.addLayout(mon_layout)
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

        trigger_layout = QHBoxLayout()
        lbl_trig = QLabel("Expansion Trigger:", page_di)
        lbl_trig.setStyleSheet("font-size: 12px;")
        self.combo_expand_trigger = QComboBox(page_di)
        self.combo_expand_trigger.setFixedWidth(140)
        self.combo_expand_trigger.addItem("Hover to Expand", "hover")
        self.combo_expand_trigger.addItem("Click to Expand", "click")
        trigger_layout.addWidget(lbl_trig)
        trigger_layout.addWidget(self.combo_expand_trigger)
        trigger_layout.addStretch()
        layout_di.addLayout(trigger_layout)

        intent_layout = QHBoxLayout()
        lbl_intent = QLabel("Hover Intent Delay:", page_di)
        lbl_intent.setStyleSheet("font-size: 12px;")
        self.spn_hover_intent = QSpinBox(page_di)
        self.spn_hover_intent.setRange(0, 1000)
        self.spn_hover_intent.setSingleStep(50)
        self.spn_hover_intent.setSuffix(" ms")
        self.spn_hover_intent.setFixedWidth(130)
        self.spn_hover_intent.setFixedHeight(30)
        intent_layout.addWidget(lbl_intent)
        intent_layout.addWidget(self.spn_hover_intent)
        intent_layout.addStretch()
        layout_di.addLayout(intent_layout)

        lbl_intent_desc = QLabel(
            "Delay before hover expands the notch, preventing accidental triggers when moving mouse past the top bezel.", page_di
        )
        lbl_intent_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        lbl_intent_desc.setWordWrap(True)
        layout_di.addWidget(lbl_intent_desc)

        delay_layout = QHBoxLayout()
        lbl_delay = QLabel("Collapse Delay:", page_di)
        lbl_delay.setStyleSheet("font-size: 12px;")
        self.spn_collapse_delay = CollapseDelaySpinBox(page_di)
        delay_layout.addWidget(lbl_delay)
        delay_layout.addWidget(self.spn_collapse_delay)
        delay_layout.addStretch()
        layout_di.addLayout(delay_layout)

        lbl_delay_desc = QLabel(
            "Time in milliseconds before the expanded media card auto-collapses back to the notch upon mouse leave.", page_di
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

        # Page 4: Audio & Equalizer Settings
        page_aud = QWidget()
        layout_aud_root = QVBoxLayout(page_aud)
        layout_aud_root.setContentsMargins(0, 0, 0, 0)
        layout_aud_root.setSpacing(6)

        lbl_aud_title = QLabel("Audio & Equalizer", page_aud)
        lbl_aud_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_aud_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        layout_aud_root.addWidget(lbl_aud_title)

        lbl_aud_sub = QLabel("Configure system-wide audio boost, tone filters, and 5-band graphic equalizer.", page_aud)
        lbl_aud_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px;")
        layout_aud_root.addWidget(lbl_aud_sub)

        line_aud = QFrame(page_aud)
        line_aud.setFrameShape(QFrame.Shape.HLine)
        line_aud.setFrameShadow(QFrame.Shadow.Sunken)
        line_aud.setStyleSheet(f"color: {COLOR_BORDER.name()};")
        layout_aud_root.addWidget(line_aud)

        # Scroll Area for dense audio controls
        scroll_aud = QScrollArea(page_aud)
        scroll_aud.setWidgetResizable(True)
        scroll_aud.setFrameShape(QFrame.Shape.NoFrame)
        scroll_aud.setStyleSheet("background: transparent; border: none;")

        aud_container = QWidget()
        layout_aud = QVBoxLayout(aud_container)
        layout_aud.setContentsMargins(0, 4, 12, 4)
        layout_aud.setSpacing(10)

        # 1. Equalizer APO Status Card
        card_apo = QFrame(aud_container)
        card_apo.setStyleSheet(
            f"background-color: {COLOR_BG_MANTLE.name()}; border: 1px solid {COLOR_BORDER.name()}; border-radius: 6px; padding: 4px;"
        )
        layout_card = QHBoxLayout(card_apo)
        layout_card.setContentsMargins(8, 6, 8, 6)
        layout_card.setSpacing(10)

        is_apo_installed = self._apo_manager.is_installed()
        if is_apo_installed:
            lbl_apo_status = QLabel("● System-wide audio boost & EQ active (Equalizer APO)", card_apo)
            lbl_apo_status.setStyleSheet("color: #00FF7F; font-size: 11px; font-weight: bold;")
            layout_card.addWidget(lbl_apo_status, 1)
        else:
            lbl_apo_status = QLabel("○ Equalizer APO not detected. Visualizer EQ active.", card_apo)
            lbl_apo_status.setStyleSheet("color: #E0AF68; font-size: 11px;")
            btn_install_apo = QPushButton("Install Driver...", card_apo)
            btn_install_apo.setFixedHeight(24)
            btn_install_apo.setStyleSheet(get_button_stylesheet())
            btn_install_apo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(EQUALIZER_APO_DOWNLOAD_URL)))
            layout_card.addWidget(lbl_apo_status, 1)
            layout_card.addWidget(btn_install_apo)

        self.chk_eq_enabled = QCheckBox("Enable EQ & Enhancements", card_apo)
        self.chk_eq_enabled.stateChanged.connect(self._on_audio_control_changed)
        layout_card.addWidget(self.chk_eq_enabled)
        layout_aud.addWidget(card_apo)

        spec_layout = QHBoxLayout()
        lbl_spec = QLabel("Visualizer Spectrum Mode:", aud_container)
        lbl_spec.setStyleSheet("font-size: 11px;")
        self.combo_spectrum_mode = QComboBox(aud_container)
        self.combo_spectrum_mode.setFixedWidth(200)
        self.combo_spectrum_mode.addItem("True FFT Frequency Spectrum", "fft")
        self.combo_spectrum_mode.addItem("Time-Domain RMS Energy", "rms")
        spec_layout.addWidget(lbl_spec)
        spec_layout.addWidget(self.combo_spectrum_mode)
        spec_layout.addStretch()
        layout_aud.addLayout(spec_layout)

        slider_qss = (
            "QSlider::groove:horizontal { height: 4px; background: #2A2A2A; border-radius: 2px; }"
            "QSlider::sub-page:horizontal { background: #00FF7F; border-radius: 2px; }"
            "QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #141414; width: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }"
        )

        # 2. Audio Boost (Preamp) Section
        boost_box = QWidget(aud_container)
        boost_l = QVBoxLayout(boost_box)
        boost_l.setContentsMargins(0, 0, 0, 0)
        boost_l.setSpacing(2)

        boost_hdr = QHBoxLayout()
        lbl_preamp_title = QLabel("Audio Boost (Preamp):", boost_box)
        lbl_preamp_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_preamp_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
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

        lbl_boost_hint = QLabel("Amplifies system volume output up to +12 dB and scales visualizer reactivity.", boost_box)
        lbl_boost_hint.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 10px;")
        boost_l.addWidget(lbl_boost_hint)
        layout_aud.addWidget(boost_box)

        # 3. Quick Tone Controls (Bass, Clarity, Treble, Noise Filter)
        tone_box = QWidget(aud_container)
        tone_l = QVBoxLayout(tone_box)
        tone_l.setContentsMargins(0, 0, 0, 0)
        tone_l.setSpacing(4)

        lbl_tone_title = QLabel("Tone & Noise Controls:", tone_box)
        lbl_tone_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_tone_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        tone_l.addWidget(lbl_tone_title)

        grid_tones = QHBoxLayout()
        # Left column: Bass & Clarity
        col1 = QVBoxLayout()
        col1.setSpacing(3)
        # Bass
        h_bass = QHBoxLayout()
        h_bass.addWidget(QLabel("Bass (Low-Shelf):"))
        self.lbl_bass_val = QLabel("0.0 dB")
        self.lbl_bass_val.setStyleSheet("color: #89B4FA; font-size: 10px;")
        h_bass.addStretch()
        h_bass.addWidget(self.lbl_bass_val)
        self.sld_bass = QSlider(Qt.Orientation.Horizontal)
        self.sld_bass.setRange(-120, 120)
        self.sld_bass.setValue(0)
        self.sld_bass.setStyleSheet(slider_qss)
        self.sld_bass.valueChanged.connect(self._on_audio_control_changed)
        col1.addLayout(h_bass)
        col1.addWidget(self.sld_bass)

        # Clarity
        h_clarity = QHBoxLayout()
        h_clarity.addWidget(QLabel("Vocal Clarity:"))
        self.lbl_clarity_val = QLabel("0.0 dB")
        self.lbl_clarity_val.setStyleSheet("color: #89B4FA; font-size: 10px;")
        h_clarity.addStretch()
        h_clarity.addWidget(self.lbl_clarity_val)
        self.sld_clarity = QSlider(Qt.Orientation.Horizontal)
        self.sld_clarity.setRange(-120, 120)
        self.sld_clarity.setValue(0)
        self.sld_clarity.setStyleSheet(slider_qss)
        self.sld_clarity.valueChanged.connect(self._on_audio_control_changed)
        col1.addLayout(h_clarity)
        col1.addWidget(self.sld_clarity)
        grid_tones.addLayout(col1)

        # Right column: Treble & Noise Gate
        col2 = QVBoxLayout()
        col2.setSpacing(3)
        # Treble
        h_treble = QHBoxLayout()
        h_treble.addWidget(QLabel("Treble / Air:"))
        self.lbl_treble_val = QLabel("0.0 dB")
        self.lbl_treble_val.setStyleSheet("color: #89B4FA; font-size: 10px;")
        h_treble.addStretch()
        h_treble.addWidget(self.lbl_treble_val)
        self.sld_treble = QSlider(Qt.Orientation.Horizontal)
        self.sld_treble.setRange(-120, 120)
        self.sld_treble.setValue(0)
        self.sld_treble.setStyleSheet(slider_qss)
        self.sld_treble.valueChanged.connect(self._on_audio_control_changed)
        col2.addLayout(h_treble)
        col2.addWidget(self.sld_treble)

        # Noise Filter
        h_noise = QHBoxLayout()
        h_noise.addWidget(QLabel("Noise Filter:"))
        self.lbl_noise_gate_val = QLabel("5%")
        self.lbl_noise_gate_val.setStyleSheet("color: #89B4FA; font-size: 10px;")
        h_noise.addStretch()
        h_noise.addWidget(self.lbl_noise_gate_val)
        self.sld_noise_gate = QSlider(Qt.Orientation.Horizontal)
        self.sld_noise_gate.setRange(0, 50)
        self.sld_noise_gate.setValue(5)
        self.sld_noise_gate.setStyleSheet(slider_qss)
        self.sld_noise_gate.valueChanged.connect(self._on_audio_control_changed)
        col2.addLayout(h_noise)
        col2.addWidget(self.sld_noise_gate)
        grid_tones.addLayout(col2)

        tone_l.addLayout(grid_tones)
        layout_aud.addWidget(tone_box)

        # 4. 5-Band Equalizer Section
        eq_box = QWidget(aud_container)
        eq_l = QVBoxLayout(eq_box)
        eq_l.setContentsMargins(0, 0, 0, 0)
        eq_l.setSpacing(4)

        eq_hdr = QHBoxLayout()
        lbl_eq_title = QLabel("5-Band Equalizer:", eq_box)
        lbl_eq_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_eq_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY.name()};")
        eq_hdr.addWidget(lbl_eq_title)
        eq_hdr.addStretch()

        self.cmb_preset = QComboBox(eq_box)
        self.cmb_preset.addItems(["Flat", "Bass Boost", "Vocal Clarity", "Electronic", "Rock", "Acoustic", "Custom"])
        self.cmb_preset.setStyleSheet(
            f"QComboBox {{ background-color: {COLOR_BG_MANTLE.name()}; border: 1px solid {COLOR_BORDER.name()}; border-radius: 4px; padding: 2px 8px; color: {COLOR_TEXT_PRIMARY.name()}; font-size: 11px; }} QComboBox QAbstractItemView {{ background-color: {COLOR_BG_BASE.name()}; color: {COLOR_TEXT_PRIMARY.name()}; selection-background-color: {COLOR_BG_SURFACE.name()}; }}"
        )
        self.cmb_preset.currentTextChanged.connect(self._on_preset_changed)
        eq_hdr.addWidget(self.cmb_preset)

        self.btn_reset_eq = QPushButton("Reset Flat", eq_box)
        self.btn_reset_eq.setFixedHeight(24)
        self.btn_reset_eq.setStyleSheet(get_button_stylesheet())
        self.btn_reset_eq.clicked.connect(self._reset_eq_flat)
        eq_hdr.addWidget(self.btn_reset_eq)
        eq_l.addLayout(eq_hdr)

        # 5 Equalizer Sliders
        eq_bands_layout = QHBoxLayout()
        eq_bands_layout.setSpacing(8)

        self.eq_band_sliders: List[QSlider] = []
        self.eq_band_labels: List[QLabel] = []
        freq_names = ["60 Hz", "250 Hz", "1 kHz", "4 kHz", "16 kHz"]

        for i, name in enumerate(freq_names):
            band_col = QVBoxLayout()
            band_col.setSpacing(2)
            lbl_freq = QLabel(name)
            lbl_freq.setStyleSheet(f"color: {COLOR_TEXT_MUTED.name()}; font-size: 10px; font-weight: bold;")
            lbl_freq.setAlignment(Qt.AlignmentFlag.AlignCenter)

            sld = QSlider(Qt.Orientation.Vertical)
            sld.setFixedHeight(60)
            sld.setRange(-120, 120)
            sld.setValue(0)
            sld.setStyleSheet(
                "QSlider::groove:vertical { width: 4px; background: #2A2A2A; border-radius: 2px; }"
                "QSlider::sub-page:vertical { background: #2A2A2A; border-radius: 2px; }"
                "QSlider::add-page:vertical { background: #00FF7F; border-radius: 2px; }"
                "QSlider::handle:vertical { background: #FFFFFF; border: 1px solid #141414; height: 12px; margin-left: -4px; margin-right: -4px; border-radius: 6px; }"
            )
            sld.valueChanged.connect(self._on_band_slider_changed)

            lbl_v = QLabel("0.0")
            lbl_v.setStyleSheet("color: #8A8A8A; font-size: 9px;")
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)

            band_col.addWidget(lbl_freq)
            band_col.addWidget(sld, 0, Qt.AlignmentFlag.AlignCenter)
            band_col.addWidget(lbl_v)
            eq_bands_layout.addLayout(band_col)

            self.eq_band_sliders.append(sld)
            self.eq_band_labels.append(lbl_v)

        # Direct property accessors for bands
        self.sld_band_60 = self.eq_band_sliders[0]
        self.sld_band_250 = self.eq_band_sliders[1]
        self.sld_band_1000 = self.eq_band_sliders[2]
        self.sld_band_4000 = self.eq_band_sliders[3]
        self.sld_band_16000 = self.eq_band_sliders[4]

        eq_l.addLayout(eq_bands_layout)
        layout_aud.addWidget(eq_box)

        scroll_aud.setWidget(aud_container)
        layout_aud_root.addWidget(scroll_aud)

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

        # Audio & Equalizer Settings
        self._is_updating_ui = True
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
        self._on_audio_control_changed()

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
