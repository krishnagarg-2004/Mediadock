from typing import Optional, Any
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
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
)

from src.core.settings import SettingsManager
from src.ui.theme import (
    COLOR_BG_BASE,
    COLOR_BG_SURFACE,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT_BLUE,
    get_button_stylesheet,
)


class SettingsDialog(QDialog):
    """Lightweight preferences dialog for MediaDock using Catppuccin Mocha styling."""

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
        self.setFixedSize(360, 480)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self._init_ui()
        self.load_settings()


    def _init_ui(self) -> None:
        """Initialize dialog widgets, layout, and Catppuccin stylesheet."""
        self.setStyleSheet(
            f"QDialog {{ background-color: {COLOR_BG_BASE.name()}; color: {COLOR_TEXT_PRIMARY.name()}; }}"
            f"QLabel {{ color: {COLOR_TEXT_PRIMARY.name()}; }}"
            f"QCheckBox {{ color: {COLOR_TEXT_PRIMARY.name()}; font-size: 13px; spacing: 8px; }}"
            f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {COLOR_BORDER.name()}; background-color: {COLOR_BG_SURFACE.name()}; }}"
            f"QCheckBox::indicator:checked {{ background-color: {COLOR_ACCENT_BLUE.name()}; border: 1px solid {COLOR_ACCENT_BLUE.name()}; }}"
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 18, 20, 18)
        root_layout.setSpacing(10)

        # Title Header
        title_label = QLabel("Preferences", self)
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        title_label.setFont(title_font)
        root_layout.addWidget(title_label)

        # Separator line
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet(f"color: {COLOR_BORDER.name()};")
        root_layout.addWidget(line)

        # Checkbox 1: Close to Tray
        self.chk_close_to_tray = QCheckBox("Close to System Tray", self)
        self.lbl_close_to_tray_desc = QLabel(
            "Closing window or pressing Escape hides MediaDock to tray", self
        )
        self.lbl_close_to_tray_desc.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;"
        )

        # Checkbox 2: Start Hidden
        self.chk_start_hidden = QCheckBox("Start Minimized to Tray", self)
        self.lbl_start_hidden_desc = QLabel(
            "Launch application in background system tray", self
        )
        self.lbl_start_hidden_desc.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;"
        )

        # Checkbox 3: Start with Windows
        self.chk_autostart_windows = QCheckBox("Start with Windows", self)
        self.lbl_autostart_windows_desc = QLabel(
            "Automatically launch MediaDock when Windows starts", self
        )
        self.lbl_autostart_windows_desc.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;"
        )

        # Checkbox 4: Always on Top
        self.chk_always_on_top = QCheckBox("Always on Top", self)
        self.lbl_always_on_top_desc = QLabel(
            "Keep widget floating above other windows", self
        )
        self.lbl_always_on_top_desc.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;"
        )

        # Checkbox 5: Remember Position
        self.chk_remember_position = QCheckBox("Remember Window Position", self)
        self.lbl_remember_position_desc = QLabel(
            "Save and restore screen coordinates", self
        )
        self.lbl_remember_position_desc.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED.name()}; font-size: 11px; margin-left: 24px;"
        )

        root_layout.addWidget(self.chk_close_to_tray)
        root_layout.addWidget(self.lbl_close_to_tray_desc)

        root_layout.addWidget(self.chk_start_hidden)
        root_layout.addWidget(self.lbl_start_hidden_desc)

        root_layout.addWidget(self.chk_autostart_windows)
        root_layout.addWidget(self.lbl_autostart_windows_desc)

        root_layout.addWidget(self.chk_always_on_top)
        root_layout.addWidget(self.lbl_always_on_top_desc)

        root_layout.addWidget(self.chk_remember_position)
        root_layout.addWidget(self.lbl_remember_position_desc)

        # Hotkeys Section Header
        line_hk = QFrame(self)
        line_hk.setFrameShape(QFrame.Shape.HLine)
        line_hk.setFrameShadow(QFrame.Shadow.Sunken)
        line_hk.setStyleSheet(f"color: {COLOR_BORDER.name()};")
        root_layout.addWidget(line_hk)

        lbl_hk_header = QLabel("Global Shortcuts", self)
        lbl_hk_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        root_layout.addWidget(lbl_hk_header)

        # Hotkey 1: Show/Hide
        hk_sh_layout = QHBoxLayout()
        lbl_hk_sh = QLabel("Show/Hide:", self)
        lbl_hk_sh.setFixedWidth(85)
        self.txt_hotkey_show_hide = QLineEdit(self)
        self.txt_hotkey_show_hide.setStyleSheet(
            f"QLineEdit {{ background-color: {COLOR_BG_SURFACE.name()}; color: {COLOR_TEXT_PRIMARY.name()}; border: 1px solid {COLOR_BORDER.name()}; border-radius: 4px; padding: 3px 6px; font-size: 12px; }}"
        )
        hk_sh_layout.addWidget(lbl_hk_sh)
        hk_sh_layout.addWidget(self.txt_hotkey_show_hide)
        root_layout.addLayout(hk_sh_layout)

        # Hotkey 2: Play/Pause
        hk_pp_layout = QHBoxLayout()
        lbl_hk_pp = QLabel("Play/Pause:", self)
        lbl_hk_pp.setFixedWidth(85)
        self.txt_hotkey_play_pause = QLineEdit(self)
        self.txt_hotkey_play_pause.setStyleSheet(
            f"QLineEdit {{ background-color: {COLOR_BG_SURFACE.name()}; color: {COLOR_TEXT_PRIMARY.name()}; border: 1px solid {COLOR_BORDER.name()}; border-radius: 4px; padding: 3px 6px; font-size: 12px; }}"
        )
        hk_pp_layout.addWidget(lbl_hk_pp)
        hk_pp_layout.addWidget(self.txt_hotkey_play_pause)
        root_layout.addLayout(hk_pp_layout)

        # Error notification label
        self.lbl_error = QLabel("", self)
        self.lbl_error.setStyleSheet("color: #F38BA8; font-size: 11px;")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        root_layout.addWidget(self.lbl_error)

        root_layout.addStretch()

        # Bottom Button Bar: Save / Cancel
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        btn_style = get_button_stylesheet()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setFixedSize(70, 28)
        self.btn_cancel.setStyleSheet(btn_style)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save", self)
        self.btn_save.setFixedSize(70, 28)
        self.btn_save.setStyleSheet(btn_style)
        self.btn_save.clicked.connect(self.save_settings)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)

        root_layout.addLayout(btn_layout)

    def load_settings(self) -> None:
        """Load current preference values from SettingsManager into checkbox and hotkey fields."""
        self.chk_close_to_tray.setChecked(self._settings_manager.get_close_to_tray())
        self.chk_start_hidden.setChecked(self._settings_manager.get_start_hidden())
        self.chk_autostart_windows.setChecked(
            self._settings_manager.get_autostart_windows()
        )
        self.chk_always_on_top.setChecked(self._settings_manager.get_always_on_top())
        self.chk_remember_position.setChecked(
            self._settings_manager.get_remember_position()
        )
        self.txt_hotkey_show_hide.setText(self._settings_manager.get_hotkey_show_hide())
        self.txt_hotkey_play_pause.setText(self._settings_manager.get_hotkey_play_pause())

    def save_settings(self) -> None:
        """Persist settings to SettingsManager and rebind hotkeys safely."""
        sh_val = self.txt_hotkey_show_hide.text().strip()
        pp_val = self.txt_hotkey_play_pause.text().strip()

        if self._hotkey_manager and hasattr(self._hotkey_manager, "rebind_hotkeys"):
            success = self._hotkey_manager.rebind_hotkeys(sh_val, pp_val)
            if not success:
                self.lbl_error.setText(
                    "Failed to bind hotkeys. Shortcut may be invalid, missing a modifier (Ctrl/Alt/Shift/Win), duplicate, or in use by another application."
                )
                self.lbl_error.show()
                return

        self.lbl_error.hide()

        self._settings_manager.set_hotkey_show_hide(sh_val)
        self._settings_manager.set_hotkey_play_pause(pp_val)

        self._settings_manager.set_close_to_tray(self.chk_close_to_tray.isChecked())
        self._settings_manager.set_start_hidden(self.chk_start_hidden.isChecked())
        self._settings_manager.set_autostart_windows(
            self.chk_autostart_windows.isChecked()
        )
        self._settings_manager.set_always_on_top(self.chk_always_on_top.isChecked())
        self._settings_manager.set_remember_position(
            self.chk_remember_position.isChecked()
        )
        self.accept()
