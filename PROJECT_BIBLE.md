# MediaDock Project Bible

This document serves as the authoritative source of truth for **MediaDock**. It defines the product identity, current implemented functionality, system architecture, technology stack, application lifecycle, development rules, and future roadmap.

---

## 1. Project Identity

- **Project Name**: MediaDock
- **Executable Name**: `MediaDock.exe`
- **Platform**: Windows Desktop (Windows 10 / 11)
- **Target Audience**: Windows desktop users desiring non-intrusive, universal media controls.

**MediaDock** is a native Windows desktop media platform whose primary user interface is a floating media widget.

### Core Identity Guidelines:
1. **Name Stability**: "MediaDock" is the official project name. Do not rename the project, executable, package, repository, or application icon.
2. **Universal Scope**: MediaDock is designed as a universal Windows media platform, not a Spotify-only tool. It integrates with any media application exposing the Windows Global System Media Transport Controls (GSMTC) API, including:
   - Spotify
   - Google Chrome
   - Microsoft Edge
   - VLC Media Player
   - Apple Music
   - Other GSMTC-compliant desktop or web media players
3. **Architecture Reusability**: The core media engine ([`MediaCore`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/media_core.py)) is kept independent of the visual presentation layer so it can be reused in future systems (such as Krishna OS) or alternative frontends.

---

## 2. Product Definition

MediaDock runs as a lightweight, background desktop utility that monitors system-wide audio and media playback in real-time. It acts as an ambient overlay, allowing users to view metadata (track title, artist, album art, position) and issue media playback commands (play/pause, skip, volume adjustment, mute) without leaving their active workflow.

---

## 3. Product Vision

The long-term vision for MediaDock is an unobtrusive desktop companion that seamlessly blends into the operating system environment:

- **Silent Background Operation**: MediaDock starts with Windows (or on demand) silently in the background, listening for media sessions without requiring user intervention.
- **Dynamic Session Awareness**: As soon as a user starts playing audio in Spotify, a web browser, or a media player, MediaDock detects the active GSMTC session and presents media controls.
- **Ambient & Non-Intrusive**: When playback stops or a media application closes, MediaDock returns to an idle/collapsed or hidden state while continuing to wait for future media sessions.
- **Decoupled Architecture**: MediaDock Core and the visible floating widget are treated as separate components. The core stays active in the system tray regardless of whether the widget is currently rendered.

---

## 4. User Experience & Future UI Direction

### Current Interface Overview
The current interface is a frameless, dark-themed floating desktop dock built with PySide6 and styled using the Catppuccin Mocha color palette. It supports full and compact view modes, desktop edge snapping, dynamic accent coloring based on album art, master volume controls, and global hotkeys.

### Future UI Direction: Dynamic Island Widget
The intended future visual design for MediaDock is a **Dynamic Island-style floating media widget**, inspired by modern mobile overlay controls:

```
+-------------------------------------------------------------+
|  [Collapsed State]                                          |
|  ( Small unobtrusive pill near top of screen: ♪ Song Title ) |
+-------------------------------------------------------------+
                              │
                    ( Hover / Click / Active )
                              ▼
+-------------------------------------------------------------+
|  [Expanded State]                                           |
|  ┌──────────┐  Die With A Smile                             |
|  │  Album   │  Lady Gaga • Bruno Mars                       |
|  │   Art    │  ████████────── 1:35 / 3:47                   |
|  └──────────┘  ⏮   ▶️   ⏭   🔊 [━━━━━━━●──]                |
+-------------------------------------------------------------+
```

- **Collapsed State**: A compact, minimal floating pill element positioned near the top of the display.
- **Expanded State**: Displays high-resolution album artwork, track title, artist name, playback status, track position slider, transport controls, and master volume/mute controls.
- **Floating Overlay Behavior**: Operates as an always-on-top, non-intrusive frameless overlay that remains usable while other desktop applications are focused.

> [!NOTE]
> The Dynamic Island UI description represents the intended **future UI direction**. The visual interface is **NOT** being redesigned during the current development phase.

---

## 5. Current Feature Set (Milestone 7 Implemented State)

MediaDock has completed **Milestone 7** and contains verified, production-ready functionality. The codebase includes an automated test suite of **138 passing unit and integration tests**.

### Implemented Features:
- **Universal GSMTC Media Detection**: Automatically detects active Windows media sessions and extracts track metadata (title, artist, album, duration, position, album art bytes) via PyWinRT ([`GSMTCProvider`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/media/gsmtc_provider.py)).
- **Multi-Session Management & Selection**: Enumerates all active system media sessions ([`MediaSessionInfo`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/models.py#L38-L47)) and allows explicit app selection (e.g. Spotify vs Chrome vs VLC) via the System Tray menu.
- **Automatic Session Fallback**: Detects session closure or termination and automatically falls back to any remaining active playing media session.
- **Master Volume & Mute Control**: Controls Windows system master volume and mute state using CoreAudio COM interfaces ([`IAudioEndpointVolume`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/media/volume_provider.py)). Safely degrades with unsupported state handling when audio endpoints are missing.
- **Configurable Global Hotkeys**: OS-wide shortcut support via Win32 `WM_HOTKEY` ([`GlobalHotkeyManager`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/hotkeys.py)). Features human-readable sequence parsing (e.g. `Ctrl+Alt+M`), shortcut collision detection, and safe configuration rollback.
- **Compact View Mode**: Toggleable view states between Full Mode (360x140 px) and Compact Mode (240x48 px) mini widget.
- **Desktop Edge Snapping**: Snaps floating window to top, bottom, left, and right desktop edges within a 15 px threshold ([`FramelessWindow`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/frameless_window.py)), supporting multi-monitor setups and DPI scaling.
- **Frameless Drag-and-Drop Container**: Custom frameless widget with drag movement, Catppuccin Mocha visual tokens, and smooth status transitions ([`MainWindow`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/main_window.py)).
- **Dynamic Accent Tinting**: Extracts dominant colors from track album artwork to tint background glow overlays ([`src/ui/theme.py`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/theme.py)).
- **System Tray Integration**: Vector tray icon, context menu, dynamic tooltips (`MediaDock - Title by Artist`), media source selector submenu, and window show/hide toggles ([`SystemTrayIcon`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/system_tray.py)).
- **Settings Persistence**: Manages preferences (`close_to_tray`, `start_hidden`, `always_on_top`, `remember_position`, `compact_mode`, `autostart`, custom hotkeys) via Qt [`SettingsManager`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/settings.py).
- **Windows Autostart Integration**: Manages HKCU registry keys (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) for optional Windows startup ([`AutostartManager`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/utils/autostart.py)).
- **Standalone Packaging**: PyInstaller build specification ([`MediaDock.spec`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/MediaDock.spec)) and build script ([`scripts/build.py`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/scripts/build.py)) generating a standalone executable (`dist/MediaDock.exe`).
- **Comprehensive Test Suite**: **138 unit and integration tests** verifying core models, media providers, volume providers, hotkey parsing, settings, UI components, and packaging specifications.

---

## 6. Current Architecture

MediaDock enforces strict separation of concerns across a 4-tier Clean Architecture:

```
                    ┌─────────────────────────┐
                    │    Presentation Layer   │
                    │       (src/ui/)         │
                    └────────────┬────────────┘
                                 │ Qt Signals / Slots
                                 ▼
                    ┌─────────────────────────┐
                    │   Application / Core    │
                    │       (src/core/)       │
                    └────────────┬────────────┘
                                 │ Abstraction Contracts
                                 ▼
                    ┌─────────────────────────┐
                    │   Domain / Model Layer  │
                    │   (src/core/models.py)  │
                    └────────────┬────────────┘
                                 │ Provider Interfaces
                                 ▼
                    ┌─────────────────────────┐
                    │  Infrastructure Layer   │
                    │ (src/media & src/utils) │
                    └─────────────────────────┘
```

### Layer Descriptions:
1. **Presentation Layer (`src/ui/`)**:
   - Contains PySide6 GUI widgets: [`MainWindow`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/main_window.py), [`FramelessWindow`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/frameless_window.py), [`SystemTrayIcon`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/system_tray.py), [`SettingsDialog`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/settings_dialog.py), [`ElidedLabel`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/components.py), and [`GlobalHotkeyManager`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/hotkeys.py).
   - Renders visual state and captures user interactions without invoking platform APIs directly.
2. **Application / Core Layer (`src/core/`)**:
   - [`MediaCore`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/media_core.py): Central thread-safe Qt coordinator extending `QObject`. Bridges background media/volume events to Qt signals (`track_changed`, `playback_status_changed`, `sessions_changed`, `volume_changed`).
   - [`SettingsManager`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/settings.py): Application preferences layer wrapping `QSettings`.
3. **Domain / Model Layer (`src/core/models.py`)**:
   - Pure, immutable data structures: [`TrackInfo`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/models.py#L12), [`PlaybackStatus`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/models.py#L29), [`MediaSessionInfo`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/models.py#L38), and [`VolumeState`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/models.py#L50).
4. **Infrastructure Layer (`src/media/` & `src/utils/`)**:
   - [`BaseMediaProvider`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/media/base_provider.py) & [`GSMTCProvider`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/media/gsmtc_provider.py): WinRT GSMTC session listener running on a dedicated background asyncio thread.
   - [`BaseVolumeProvider`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/media/volume_provider.py#L11) & [`WindowsVolumeProvider`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/media/volume_provider.py#L51): CoreAudio COM integration via `ctypes`.
   - [`AutostartManager`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/utils/autostart.py): Windows Registry (`winreg`) integration.

---

## 7. Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.14 | Core programming language |
| **GUI Framework** | PySide6 (Qt 6 for Python) | Desktop UI rendering, event loop, and signal/slot infrastructure |
| **Media API** | PyWinRT (`winsdk` / `winrt`) | Windows Global System Media Transport Controls (GSMTC) integration |
| **Volume Control** | Win32 `ctypes` COM | CoreAudio `IAudioEndpointVolume` (`CLSID_MMDeviceEnumerator`) |
| **Global Hotkeys** | Win32 API (`user32.dll`) | Low-level `RegisterHotKey` / `UnregisterHotKey` hook via `WM_HOTKEY` |
| **Registry API** | Python `winreg` | Windows startup registry configuration |
| **Image Processing**| Pillow (PIL) | Album art byte parsing and dominant color extraction |
| **Async Engine** | `asyncio` | Background event loop for WinRT async notifications |
| **Packaging** | PyInstaller | Single-file windowed executable generation (`dist/MediaDock.exe`) |
| **Testing** | Standard `unittest` | Automated unit and integration testing (**138 tests**) |

---

## 8. Repository Structure

```
MediaDock/
├── .gitignore                      # Git exclusion rules
├── .venv/                          # Local Python 3.14 virtual environment
├── AI_RULES.md                     # Workspace AI guidance rules
├── LICENSE.txt                     # License file
├── MediaDock.spec                  # PyInstaller build specification
├── PROJECT_BIBLE.md                # Authoritative project document (this file)
├── PROJECT_STATUS.md               # Milestone tracking and release status
├── README.md                       # Project overview and quickstart guide
├── requirements.txt                # Python package dependencies
├── assets/                         # Application icons and visual resources
├── build/                          # Temporary build artifacts
├── dist/                           # Output directory for standalone MediaDock.exe
├── docs/                           # Documentation suite
│   ├── architecture.md             # Technical Architecture Manual
│   └── user_guide.md                # User & Operations Manual
├── scripts/                        # Automation scripts
│   └── build.py                    # PyInstaller executable build script
├── src/                            # Application source code
│   ├── __init__.py
│   ├── main.py                     # Application entry point
│   ├── core/                       # Core domain models and state coordination
│   │   ├── __init__.py
│   │   ├── media_core.py           # Thread-safe Qt signal bridge & facade
│   │   ├── models.py               # Immutable domain models (TrackInfo, etc.)
│   │   └── settings.py             # Qt QSettings wrapper
│   ├── media/                      # Media and volume provider implementations
│   │   ├── __init__.py
│   │   ├── base_provider.py        # Abstract media provider interface
│   │   ├── gsmtc_provider.py       # WinRT GSMTC multi-session provider
│   │   └── volume_provider.py      # CoreAudio COM master volume provider
│   ├── ui/                         # PySide6 user interface components
│   │   ├── __init__.py
│   │   ├── components.py           # ElidedLabel and custom UI components
│   │   ├── frameless_window.py     # Dragging and screen edge snapping window
│   │   ├── hotkeys.py              # Win32 global hotkey registration & parsing
│   │   ├── main_window.py          # Primary dock window (Full & Compact modes)
│   │   ├── settings_dialog.py      # Configuration GUI dialog
│   │   ├── system_tray.py          # System tray icon & context menus
│   │   └── theme.py                # Catppuccin Mocha tokens & color extraction
│   └── utils/                      # OS helper modules
│       ├── __init__.py
│       └── autostart.py            # Windows Registry autostart integration
└── tests/                          # Automated test suite (138 tests)
    ├── test_autostart.py
    ├── test_base_provider.py
    ├── test_build_spec.py
    ├── test_compact_mode_and_snapping.py
    ├── test_gsmtc_provider.py
    ├── test_hotkeys.py
    ├── test_integration_step5.py
    ├── test_media_core.py
    ├── test_models.py
    ├── test_multi_session.py
    ├── test_settings.py
    ├── test_settings_dialog.py
    ├── test_system_tray.py
    ├── test_ui_theme.py
    ├── test_volume_provider.py
    └── test_window.py
```

---

## 9. Application Lifecycle

MediaDock operates as a persistent desktop utility with well-defined lifecycle rules.

### Required Lifecycle Behaviors:

#### A. Silent Startup & Background Monitoring
- Windows starts → MediaDock Core starts silently in the background (when autostart is enabled or launched with `--minimized` / `--start-hidden`).
- MediaDock Core initializes media session listeners and system tray icon without requiring a media player to be active.
- When a supported media app (e.g. Spotify, Chrome) starts playing, MediaDock detects the GSMTC session and displays media controls.
- When media stops or the media app closes, MediaDock remains active in the background, placing the widget into an idle/hidden state and waiting for future sessions.

#### B. Single Instance Enforcement
- Only one instance of MediaDock may run at any time.
- If a user attempts to launch `MediaDock.exe` while an instance is already running:
  - Do NOT spawn a second widget, media controller, or tray icon.
  - Signal the running instance.
  - Bring/show/focus the existing MediaDock widget window.
  - Terminate the secondary process cleanly.

#### C. Hide / Minimize Behavior
- "Hiding" or closing the widget window does **NOT** terminate MediaDock.
- When hidden:
  - The widget UI disappears.
  - MediaDock Core remains running in the background.
  - GSMTC session monitoring and volume control remain active.
  - System tray icon remains available for user interaction.

#### D. System Tray & Context Menu
- MediaDock maintains a functional system tray icon in the Windows taskbar overflow area.
- Tray Context Menu Structure:
  ```
  MediaDock
  ----------------
  Show Widget / Hide Widget
  Compact Mode
  Media Source >
  Settings
  ----------------
  Exit MediaDock
  ```
- **System Tray Reliability**: The system tray icon must initialize reliably on application startup across all Windows display configurations.

#### E. Clean Exit
- Triggering "Exit MediaDock" from the system tray menu terminates the process cleanly:
  - Unregisters global hotkeys (`UnregisterHotKey`).
  - Stops the background asyncio media loop and WinRT listeners.
  - Hides and disposes of the system tray icon.
  - Exits the Qt event loop (`app.quit()`).

---

## 10. Media Detection Architecture

Media detection relies on WinRT GSMTC (`GlobalSystemMediaTransportControlsSessionManager`):

```
┌─────────────────────────────────────────────────────────────┐
│                    Windows GSMTC API                        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Async WinRT Events
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       GSMTCProvider                         │
│       - Runs on dedicated background asyncio thread         │
│       - Monitors session updates, metadata & timeline       │
│       - Formats app display names (Spotify, Chrome, etc.)   │
│       - Maintains multi-session list & auto-fallback        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Thread-safe Callback
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         MediaCore                           │
│       - Qt QObject facade on main GUI thread                │
│       - Emits track_changed, playback_status_changed        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Qt Signals
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               MainWindow / SystemTrayIcon                   │
└─────────────────────────────────────────────────────────────┘
```

- **Session Enumeration**: Discovers all active GSMTC sessions on the system.
- **Session Selection**: Allows targeting a specific media session (e.g., Spotify over Chrome) or defaulting to the most recently active session.
- **Automatic Fallback**: If the selected session closes, `GSMTCProvider` automatically switches to another active session or transitions to an empty/idle state.

---

## 11. UI Architecture

The UI architecture isolates window behavior, visual styling, and user interaction:

- **[`FramelessWindow`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/frameless_window.py)**: Low-level window controller implementing custom frameless window flags (`Qt.FramelessWindowHint`, `Qt.WindowStaysOnTopHint`), drag-and-drop mouse handlers, and desktop edge snapping. Edge snapping dynamically evaluates `QScreen.availableGeometry()` to snap within 15 px of screen boundaries across multi-monitor setups.
- **[`MainWindow`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/main_window.py)**: Main application container managing layout transitions between Full Mode (360x140 px) and Compact Mode (240x48 px), vector icon rendering (`QPainter`), and media control button slots.
- **[`SystemTrayIcon`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/system_tray.py)**: Encapsulates `QSystemTrayIcon`, rendering HiDPI vector icons, dynamic tooltips, and the media source selection menu.
- **[`SettingsDialog`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/ui/settings_dialog.py)**: Settings dialog managing user preferences and hotkey rebind sequence inputs.

---

## 12. Current Milestone / Project Status

- **Completed Milestones**: Milestones 1 through 7 are complete.
- **Test Suite Status**: **138 / 138 unit & integration tests passing**.
- **Executable Build**: Standalone executable `dist/MediaDock.exe` verified working.
- **Current Milestone**: Transitioning to **Next Development Phase: MediaDock Reliability & Desktop Lifecycle**.

---

## 13. Known Issues

The following technical issues are prioritized for resolution in the upcoming development phase:

1. **System Tray Icon Reliability**: In certain startup scenarios, the system tray icon does not appear reliably in the Windows taskbar notification area.
2. **Session Startup Coupling**: Initial startup logic currently assumes an active media session is present; needs full decoupling to ensure background startup when no media applications are running.

---

## 14. Next Development Phase

### Phase Title: MediaDock Reliability & Desktop Lifecycle

The next development phase focuses exclusively on application lifecycle robustification, single-instance process management, system tray reliability, and startup decoupling.

### Priority Roadmap:

1. **Media Session Lifecycle & Decoupling**:
   - MediaDock starts cleanly before Spotify or any media app is opened.
   - MediaDock dynamically detects Spotify/media apps launched after MediaDock startup.
   - MediaDock handles media app closure and session disappearance gracefully.
   - MediaDock remains running in the background when Spotify or media apps close.
2. **Single-Instance Application Enforcement**:
   - Ensure strictly one running process of MediaDock.
   - Second launch detects existing instance, sends bring-to-front signal, and terminates cleanly.
3. **System Tray Icon Reliability**:
   - Investigate and resolve system tray icon initialization issues so the tray icon reliably appears on startup.
   - Verify tray context menu functionality across all display environments.
4. **Widget Lifecycle & Visibility States**:
   - Ensure robust Show, Hide, Compact, and Exit state transitions.
   - Verify clean background shutdown.
5. **Windows Autostart Verification**:
   - Verify registry-based silent autostart behavior on Windows login.
6. **Regression Testing & Packaging Verification**:
   - Ensure all 138+ automated tests pass and verify updated PyInstaller build (`dist/MediaDock.exe`).

### Explicit Negative Constraints (Do NOT do during Next Development Phase):
- ❌ Do **NOT** implement or redesign the visual UI yet.
- ❌ Do **NOT** implement Dynamic Island visuals yet.
- ❌ Do **NOT** rename the project, executable, or icon.
- ❌ Do **NOT** add Windows Widgets Board integration.
- ❌ Do **NOT** implement deferred long-term features (lyrics, visualizer, plugins, AI, etc.).

---

## 15. Deferred Features

To maintain implementation focus, the following architectural and feature proposals are explicitly deferred:

- **Custom Plugin System**: Architecture for dynamic third-party provider plugins.
- **Theme Engine**: JSON-based theme files or external visual theme packs.
- **Synchronized Lyrics**: Real-time synchronized track lyric display.
- **Audio Visualizers & Equalizer**: Real-time FFT audio waveforms and customizable EQ filters.
- **AI Features & Voice Control**: Local LLM track recommendations, artist summaries, or voice command control.
- **OBS Overlay Mode**: Specialized transparent window rendering for streamer broadcast software.
- **Discord Rich Presence**: Integration with Discord IPC for custom user status updates.
- **Stream Deck & Rainmeter Integration**: Direct hardware or desktop suite integration protocols.
- **Listening History & Analytics**: Playback stat tracking, listening streak counters, or genre charts.
- **Multiple Layout Engines**: Separate vertical, horizontal, or album-focused widget layouts.
- **Broad Desktop Widget Platform**: Expansion into a multi-widget desktop platform (Krishna Desktop Platform).

---

## 16. Long-Term Ideas

- **Module Extraction for Krishna OS**: Package `MediaCore` as a standalone Python library for integration into future operating system projects.
- **GitHub Release & Portfolio Strategy**:
  - **Phase A (Active Development)**: Maintain as a private GitHub repository during active core development and refinement.
  - **Phase B (Portfolio Evaluation)**: Once reliability, UX, and visual design reach production polish, evaluate opening the repository as a public open-source portfolio project.

---

## 17. Engineering Principles

1. **Clean Layer Separation**: Maintain strict boundaries between Presentation, Application, Domain, and Infrastructure layers.
2. **Provider Abstraction**: All media engines and audio providers must implement unified abstract interfaces ([`BaseMediaProvider`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/media/base_provider.py), [`BaseVolumeProvider`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/media/volume_provider.py#L11)).
3. **Thread Safety**: Keep WinRT and asyncio operations isolated on background threads, signaling the PySide6 main GUI thread via thread-safe Qt signals.
4. **Defensive Error Handling**: Platform API failures (such as missing CoreAudio endpoints or WinRT connection issues) must degrade gracefully into unsupported model states without crashing the application.
5. **No Premature Complexity**: Build only the abstractions required for current functionality; defer speculative infrastructure.

---

## 18. Development Rules

The following rules apply to all development on MediaDock:

1. **User Code Execution**: The user writes and commits code. The AI assistant provides explanations, architecture design, and step-by-step guidance.
2. **Architectural Rationale**: Explain the technical reasoning before proposing code modifications.
3. **Targeted Changes**: Keep code modifications isolated strictly to the active task/milestone. Do not modify unrelated features.
4. **Documentation Synchronization**: Keep `PROJECT_BIBLE.md`, `docs/architecture.md`, `docs/user_guide.md`, `README.md`, and `PROJECT_STATUS.md` synchronized with the actual codebase state.
5. **Mandatory Testing**: All changes must be verified against the automated test suite before committing.
6. **No Unnecessary Dependencies**: Avoid adding third-party dependencies unless standard library or core dependencies (PySide6, PyWinRT) cannot fulfill the requirement.
7. **Preserve Functionality**: Preserve all existing working functionality and passing tests when implementing new features.

---

## 19. Important Architectural Decisions

| Decision | Rationale |
| :--- | :--- |
| **WinRT GSMTC over Spotify Web API** | Operates 100% locally without requiring internet connectivity, OAuth authentication tokens, developer accounts, or service-specific API rate limits. Automatically supports all Windows media apps. |
| **Qt Signal Bridge (`MediaCore`)** | Isolates background asyncio WinRT loops from the PySide6 main thread, preventing UI thread blocking and ensuring thread-safe UI updates. |
| **Provider Abstraction Pattern** | Encapsulates media discovery behind [`BaseMediaProvider`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/media/base_provider.py), enabling seamless unit testing with mock providers and future media source additions. |
| **Direct Win32/CoreAudio Integration** | Uses `ctypes` COM interfaces for volume control and `user32.dll` for global hotkeys, avoiding external native C-extensions or heavy dependencies. |
| **PyInstaller Standalone Executable** | Packages Python runtime, PySide6 binaries, and PyWinRT DLLs into a single `MediaDock.exe` executable for zero-dependency end-user distribution. |

---

## 20. Development History

- **Milestone 1 — Foundation**: Established repository structure, PySide6 `QApplication` entry point, frameless window foundation, and basic event loop.
- **Milestone 2 — Windows Media Detection**: Built `GSMTCProvider` with PyWinRT integration, background asyncio thread loop, and metadata extraction (title, artist, album art, position).
- **Milestone 3 — Connected UI & Advanced Controls**: Implemented `MediaCore` Qt signal bridge, interactive UI transport controls, seeking state machine, and provider command delegation.
- **Milestone 4 — Visual Polish & Dynamic Styling**: Added Catppuccin Mocha QSS design system, `ElidedLabel` dynamic title truncating, widget opacity animations, and Pillow dominant color extraction for dynamic artwork tinting.
- **Milestone 5 — System Tray & Settings**: Implemented `SettingsManager` (`QSettings`), `SystemTrayIcon` vector icon and menus, and `SettingsDialog` preference UI.
- **Milestone 6 — Advanced Features, OS Integration & Packaging**:
  - Implemented `AutostartManager` Windows Registry integration.
  - Built `GlobalHotkeyManager` with Win32 `WM_HOTKEY` registration.
  - Created `MediaDock.spec` and `scripts/build.py` PyInstaller packaging system.
  - Authored `docs/architecture.md` and `docs/user_guide.md`.
- **Milestone 7 — Media Source & Control Expansion**:
  - Multi-session GSMTC enumeration and System Tray media app selector menu.
  - Windows Master Volume and Mute control via CoreAudio COM `IAudioEndpointVolume`.
  - Configurable global hotkeys with key sequence parsing, collision detection, and safe rollback.
  - Compact view mode (240x48 px) and 15 px multi-monitor desktop edge snapping.
  - Expanded test suite to **138 passing tests**.
