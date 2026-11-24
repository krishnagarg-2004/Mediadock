"""Application entry point for MediaDock."""

import sys
from typing import Optional
from PySide6.QtWidgets import QApplication

from src.core.settings import SettingsManager
from src.core.single_instance import SingleInstanceGuard
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

    # Single-instance enforcement: exit secondary launches early
    single_instance_guard = SingleInstanceGuard()
    if not single_instance_guard.initialize(sys.argv):
        return 0

    # Ensure clean release of server lock on exit
    app.aboutToQuit.connect(single_instance_guard.close)

    # Instantiate settings, media infrastructure, application coordinator, and hotkey manager
    settings_manager = SettingsManager()
    provider = GSMTCProvider()
    media_core = MediaCore(provider=provider, settings_manager=settings_manager)
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
            if settings_dialog is None:
                settings_dialog = SettingsDialog(
                    settings_manager=settings_manager,
                    hotkey_manager=hotkey_manager,
                    media_core=media_core,
                    parent=window,
                )
            settings_dialog.load_settings()
            settings_dialog.show()
        settings_dialog.raise_()
        settings_dialog.activateWindow()

    # Connect system tray interaction signals
    def toggle_window_visibility() -> None:
        from src.ui.main_window import DynamicIslandState
        if window.island_state == DynamicIslandState.HIDDEN:
            if settings_manager.get_dynamic_island_enabled():
                window.set_state(DynamicIslandState.COLLAPSED)
                tray_icon.update_menu_state(True)
        else:
            window.set_state(DynamicIslandState.HIDDEN)
            tray_icon.update_menu_state(False)

    def show_and_front_window() -> None:
        from src.ui.main_window import DynamicIslandState
        if window.island_state == DynamicIslandState.HIDDEN:
            window.set_state(DynamicIslandState.COLLAPSED)
        tray_icon.update_menu_state(True)

    def quit_application() -> None:
        settings_manager.sync()
        window.force_close()
        app.quit()

    tray_icon.show_hide_requested.connect(toggle_window_visibility)
    tray_icon.show_requested.connect(show_and_front_window)
    tray_icon.settings_requested.connect(open_settings_dialog)
    window.open_settings_requested.connect(open_settings_dialog)
    tray_icon.exit_requested.connect(quit_application)

    # Connect single instance activation signal
    single_instance_guard.activation_requested.connect(show_and_front_window)

    # Connect global hotkey signals
    hotkey_manager.show_hide_requested.connect(toggle_window_visibility)
    hotkey_manager.play_pause_requested.connect(media_core.toggle_play_pause)

    # Start media detection and global hotkeys using persisted settings
    sh_hk = settings_manager.get_hotkey_show_hide()
    pp_hk = settings_manager.get_hotkey_play_pause()

    media_core.start()
    hotkey_manager.start(
        show_hide_seq=sh_hk,
        play_pause_seq=pp_hk,
        target_hwnd=int(window.winId()),
    )

    # Ensure clean provider, hotkey, settings sync, and tray icon shutdown on application exit
    app.aboutToQuit.connect(settings_manager.sync)
    app.aboutToQuit.connect(hotkey_manager.stop)
    app.aboutToQuit.connect(media_core.stop)
    app.aboutToQuit.connect(tray_icon.hide_tray_icon)

    # Apply start_hidden setting or command-line flags (--minimized / --start-hidden)
    from src.ui.main_window import DynamicIslandState
    start_hidden = (
        "--minimized" in sys.argv
        or "--start-hidden" in sys.argv
        or settings_manager.get_start_hidden()
        or not settings_manager.get_dynamic_island_enabled()
    )
    if start_hidden or not media_core.is_session_available():
        window.set_state(DynamicIslandState.HIDDEN)
        tray_icon.update_menu_state(False)
    else:
        window.set_state(DynamicIslandState.COLLAPSED)
        tray_icon.update_menu_state(True)

    return app.exec()



if __name__ == "__main__":
    sys.exit(main())
