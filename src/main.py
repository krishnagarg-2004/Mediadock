"""Application entry point for MediaDock."""

import sys
from typing import Optional
from PySide6.QtWidgets import QApplication

from src.core.settings import SettingsManager
from src.media.gsmtc_provider import GSMTCProvider
from src.core.media_core import MediaCore
from src.ui.main_window import MainWindow
from src.ui.system_tray import SystemTrayIcon
from src.ui.settings_dialog import SettingsDialog
from src.ui.hotkeys import GlobalHotkeyManager


def main() -> int:
    """Initialize QApplication, SettingsManager, SystemTrayIcon, MainWindow, GlobalHotkeyManager, and start event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName("MediaDock")
    app.setOrganizationName("KrishnaOS")
    app.setQuitOnLastWindowClosed(False)

    # Instantiate settings, media infrastructure, application coordinator, and hotkey manager
    settings_manager = SettingsManager()
    provider = GSMTCProvider()
    media_core = MediaCore(provider=provider)
    hotkey_manager = GlobalHotkeyManager()

    # Instantiate GUI window and SystemTrayIcon
    window = MainWindow(media_core=media_core, settings_manager=settings_manager)
    tray_icon = SystemTrayIcon(media_core=media_core)
    tray_icon.show()

    # Settings dialog single-instance reference
    settings_dialog: Optional[SettingsDialog] = None

    def open_settings_dialog() -> None:
        nonlocal settings_dialog
        if settings_dialog is None or not settings_dialog.isVisible():
            settings_dialog = SettingsDialog(settings_manager=settings_manager, parent=window)
            settings_dialog.show()
        settings_dialog.raise_()
        settings_dialog.activateWindow()

    # Connect system tray interaction signals
    def toggle_window_visibility() -> None:
        if window.isVisible() and not window.isMinimized():
            window.hide()
            tray_icon.update_menu_state(False)
        else:
            window.show()
            window.raise_()
            window.activateWindow()
            tray_icon.update_menu_state(True)

    def show_and_front_window() -> None:
        window.show()
        window.raise_()
        window.activateWindow()
        tray_icon.update_menu_state(True)

    tray_icon.show_hide_requested.connect(toggle_window_visibility)
    tray_icon.show_requested.connect(show_and_front_window)
    tray_icon.settings_requested.connect(open_settings_dialog)
    tray_icon.exit_requested.connect(app.quit)

    # Connect global hotkey signals
    hotkey_manager.show_hide_requested.connect(toggle_window_visibility)
    hotkey_manager.play_pause_requested.connect(media_core.toggle_play_pause)

    # Start media detection and global hotkeys
    media_core.start()
    hotkey_manager.start()

    # Ensure clean provider and hotkey shutdown on application exit
    app.aboutToQuit.connect(hotkey_manager.stop)
    app.aboutToQuit.connect(media_core.stop)

    # Apply start_hidden setting
    if settings_manager.get_start_hidden():
        window.hide()
        tray_icon.update_menu_state(False)
    else:
        window.show()
        tray_icon.update_menu_state(True)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
