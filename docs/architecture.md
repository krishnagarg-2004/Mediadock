# MediaDock Technical Architecture Manual

This document provides a comprehensive technical overview of the **MediaDock** architecture, design patterns, component relationships, data models, signal flows, and OS integration layers as implemented in the repository.

---

## 1. System Overview & Component Topology

MediaDock is a modular native Windows desktop application built with **Python 3.14**, **PySide6 (Qt for Python)**, and **PyWinRT**. It functions as a floating, frameless media dock that monitors system-wide media sessions via the Windows **Global System Media Transport Controls (GSMTC)** API.

```mermaid
graph TD
    subgraph "OS & Platform Layer"
        GSMTC["Windows GSMTC API (WinRT)"]
        COREAUDIO["Windows CoreAudio API (ctypes / IAudioEndpointVolume)"]
        WINREG["Windows Registry (HKCU\\...\\Run)"]
        USER32["Win32 User32.dll (WM_HOTKEY)"]
    end

    subgraph "Media Engine Layer (src/media & src/core)"
        GSMTCProvider["GSMTCProvider\n(Background Asyncio Loop Thread)"]
        BaseProvider["BaseMediaProvider (Abstract Interface)"]
        VolumeProvider["BaseVolumeProvider / WindowsVolumeProvider\n(CoreAudio COM Integration)"]
        MediaCore["MediaCore\n(Qt Signal Bridge & Coordinator)"]
        Models["Domain Models\n(TrackInfo, PlaybackStatus, MediaSessionInfo, VolumeState)"]
    end

    subgraph "Application Core & Utility (src/core & src/utils)"
        SettingsMgr["SettingsManager\n(Qt QSettings Wrapper)"]
        AutostartMgr["AutostartManager\n(winreg Integration)"]
        MainApp["Main Entry (src/main.py)\nQApplication"]
    end

    subgraph "UI Layer (src/ui)"
        FramelessWindow["FramelessWindow\n(Edge Snapping & Dragging)"]
        MainWindow["MainWindow\n(Full 360x140 / Compact 240x48 Modes)"]
        SystemTrayIcon["SystemTrayIcon\n(Tray Menu & Source Selector)"]
        SettingsDialog["SettingsDialog\n(Preferences UI)"]
        HotkeyMgr["GlobalHotkeyManager\n(Parsing, Rebinding & Rollback)"]
    end

    GSMTC --> GSMTCProvider
    COREAUDIO --> VolumeProvider
    GSMTCProvider -- Inherits --> BaseProvider
    GSMTCProvider -- Emits Callbacks --> MediaCore
    VolumeProvider -- Emits Callbacks --> MediaCore
    MediaCore -- Uses --> Models

    MainApp --> SettingsMgr
    MainApp --> MediaCore
    MainApp --> MainWindow
    MainApp --> SystemTrayIcon
    MainApp --> HotkeyMgr

    MainWindow -- Inherits --> FramelessWindow
    MainWindow -- Observes --> MediaCore
    MainWindow -- Reads/Writes --> SettingsMgr

    SystemTrayIcon -- Observes --> MediaCore
    SystemTrayIcon -- Triggers --> MainWindow
    SystemTrayIcon -- Opens --> SettingsDialog

    SettingsDialog -- Reads/Writes --> SettingsMgr
    SettingsMgr -- Interacts --> AutostartMgr
    AutostartMgr --> WINREG

    HotkeyMgr -- Intercepts --> USER32
    HotkeyMgr -- Signals --> MainWindow
    HotkeyMgr -- Signals --> MediaCore
```

---

## 2. Component Architecture

### 2.1 Domain Models (`src/core/models.py`)
- **`TrackInfo`**: Immutable dataclass encapsulating current track metadata (`title`, `artist`, `album`, `album_art_bytes`, `app_id`, `duration_ms`, `position_ms`).
- **`PlaybackStatus`**: String Enum defining playback states (`PLAYING`, `PAUSED`, `STOPPED`, `CLOSED`, `UNKNOWN`).
- **`MediaSessionInfo`**: Immutable dataclass representing an active media session (`session_id`, `app_id`, `display_name`, `is_current`, `is_selected`).
- **`VolumeState`**: Immutable dataclass representing audio volume state (`volume_percent: int`, `is_muted: bool`, `is_supported: bool = True`). Includes `VolumeState.unsupported()` factory.

### 2.2 Provider Abstraction & Media Engine (`src/media/` & `src/core/media_core.py`)
- **`BaseMediaProvider`** (`src/media/base_provider.py`): Abstract base class defining provider interface contracts, including multi-session management methods (`get_active_sessions()`, `select_session(session_id)`).
- **`GSMTCProvider`** (`src/media/gsmtc_provider.py`): WinRT implementation supporting multi-session enumeration, app display name formatting (Spotify, Chrome, Edge, VLC), auto-fallback on session closure, and thumbnail extraction.
- **`BaseVolumeProvider` & `WindowsVolumeProvider`** (`src/media/volume_provider.py`): Windows master volume provider utilizing standard library `ctypes` COM interface `IAudioEndpointVolume` (`CLSID_MMDeviceEnumerator`). Clamps volume scalar values (0–100%) and provides mute toggling. Safely degrades to `VolumeState.unsupported()` when CoreAudio endpoints are missing or unavailable.
- **`MediaCore`** (`src/core/media_core.py`): Thread-safe Qt facade extending `QObject`. Delegates volume operations and bridges provider callbacks to Qt signals (`track_changed`, `playback_status_changed`, `session_availability_changed`, `sessions_changed`, `volume_changed`).

### 2.3 UI & Design System (`src/ui/`)
- **`FramelessWindow`** (`src/ui/frameless_window.py`): Custom frameless container widget extending `QWidget`.
  - **Desktop Edge Snapping**: Evaluates `_apply_edge_snapping(raw_pos)` during `mouseMoveEvent` dragging. Snaps within a 15 px threshold against `QScreen.availableGeometry()` (respecting taskbars across multi-monitor setups and DPI scaling).
- **`MainWindow`** (`src/ui/main_window.py`): Primary floating dock widget extending `FramelessWindow`.
  - **Full vs Compact Modes**: Toggles between Full Mode (360x140 px) and Compact Mode (240x48 px). Hides non-essential controls in compact view while keeping title elision and playback pathways identical.
  - **Vector Icons**: Renders HiDPI vector speaker mute/unmute icons (`create_volume_icon_pixmap`) using `QPainter` and `QPen`.
  - **Context Menu**: Right-click context menu offering checkable `"Compact Mode"` view action.
- **`ElidedLabel`** (`src/ui/components.py`): Custom `QLabel` subclass that dynamically formats overflowing text using `QFontMetrics.elidedText(..., Qt.ElideRight, width)`.
- **Theme System** (`src/ui/theme.py`): Catppuccin Mocha palette (`COLOR_BG_BASE = #1E1E2E`, `COLOR_TEXT_PRIMARY = #CDD6F4`, `COLOR_ACCENT_BLUE = #89B4FA`, etc.) with dynamic album-art dominant color extraction.

### 2.4 System Tray Component (`src/ui/system_tray.py`)
- **`SystemTrayIcon`**: Subclass of `QSystemTrayIcon` featuring:
  - Vector icon badge (`♪` glyph).
  - Dynamic tooltip: `"MediaDock - {title} by {artist} [{status}]"`.
  - **Media Source Submenu**: Presentation-only submenu listing active media sessions (`Spotify`, `Google Chrome`, `VLC`) for user selection.

### 2.5 Preferences & Storage Layer (`src/core/settings.py` & `src/ui/settings_dialog.py`)
- **`SettingsManager`**: Qt-native wrapper around `QSettings("KrishnaOS", "MediaDock")`.
  - Managed preferences: `close_to_tray`, `start_hidden`, `always_on_top`, `remember_position`, `compact_mode`, `hotkeys/show_hide` (default `"Ctrl+Alt+M"`), `hotkeys/play_pause` (default `"Ctrl+Alt+Space"`), `autostart`.
- **`SettingsDialog`**: Preferences configuration dialog with hotkey text fields, rebind validation error label, and `chk_compact_mode` checkbox.

### 2.6 Operating System Integration (`src/utils/autostart.py` & `src/ui/hotkeys.py`)
- **`AutostartManager`**: Windows Registry autostart under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- **`GlobalHotkeyManager`** (`src/ui/hotkeys.py`): Win32 `RegisterHotKey` global shortcut manager.
  - **Sequence Parsing**: `parse_key_sequence(sequence_str)` converts Qt-style strings into Win32 modifier bitmasks (`MOD_CONTROL`, `MOD_ALT`, `MOD_SHIFT`, `MOD_WIN`) and Virtual Key codes (`VK_SPACE`, `VK_M`, `0x41..0x5A`, `F1..F24`). Validates presence of at least one modifier key.
  - **Safe Rebinding & Rollback**: `rebind_hotkeys(show_hide_seq, play_pause_seq)` validates sequences, checks for duplicate shortcut assignments, and attempts Win32 registration. If registration fails, it automatically rolls back to the previous working shortcut configuration.

---

## 3. Application Lifecycle & Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Main as src/main.py
    participant App as QApplication
    participant Settings as SettingsManager
    participant Media as MediaCore / GSMTCProvider
    participant Hotkeys as GlobalHotkeyManager
    participant UI as MainWindow
    participant Tray as SystemTrayIcon

    Main->>App: Instantiate QApplication(sys.argv)
    Main->>App: setQuitOnLastWindowClosed(False)
    Main->>Settings: Instantiate SettingsManager()
    Main->>Media: Instantiate GSMTCProvider, WindowsVolumeProvider & MediaCore
    Main->>Hotkeys: Instantiate & start GlobalHotkeyManager(show_hide, play_pause)
    Main->>UI: Instantiate MainWindow(media_core, settings_manager)
    Main->>Tray: Instantiate & show SystemTrayIcon(media_core)

    Main->>Tray: Connect signals (show/hide, settings, session selection, exit)
    Main->>Hotkeys: Connect signals (show/hide, play/pause)
    Main->>App: Connect app.aboutToQuit -> Hotkeys.stop, Media.stop

    alt CLI arg contains --minimized / --start-hidden OR settings.start_hidden is True
        Main->>UI: window.hide()
        Main->>Tray: update_menu_state(False)
    else Normal Startup
        Main->>UI: window.show()
        Main->>Tray: update_menu_state(True)
    end

    Main->>App: app.exec()
```
