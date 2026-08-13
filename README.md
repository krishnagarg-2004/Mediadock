# MediaDock

**MediaDock** is a native Windows desktop media application built with **Python 3.14**, **PySide6 (Qt for Python)**, and **PyWinRT**. It automatically detects and controls system-wide media playback (Spotify, YouTube, VLC, Apple Music, Chrome/Edge) using the Windows **Global System Media Transport Controls (GSMTC)** API and presents a top-center **Dynamic Island** overlay.

---

## Key Features

- **Top-Center Dynamic Island Architecture**: Modern top-center anchored media widget with explicit `HIDDEN`, `COLLAPSED` (180x40 px capsule), and `EXPANDED` (360x160 px media card) state machine with smooth 180ms `OutCubic` geometry morphing centered around a constant center X coordinate. Guaranteed zero position drift across repeated hover expand/collapse transitions.
- **Fixed System Visual Identity**: Pure Black (`#000000`) capsule/card background and border, system-defined Active status green (`#00FF7F`), Inactive status red (`#C1121C`), dark charcoal (`#141414`/`#222222`) secondary surfaces, and subtle dark gray (`#2A2A2A`) borders.
- **Hover Expansion & Inactivity Collapse**: Mouse hover on capsule immediately expands to interactive media card; mouse leave starts a configurable single-shot collapse timer (default 3500 ms).
- **Universal Windows Media Detection & Multi-Session Selection**: Automatically detects active media sessions across Spotify, web browsers, and local media players via WinRT GSMTC. Select specific media apps from System Tray menu.
- **Master Volume & Mute Control**: Integrated master volume slider and mute toggle using Windows CoreAudio (`IAudioEndpointVolume`) with graceful fallback when unsupported.
- **Win32 Global Shortcuts & HWND Dispatch**: OS-wide global hotkeys (`Ctrl+Alt+S` Show/Hide, `Ctrl+Alt+Space` Play/Pause) registered directly with window HWND (`window.winId()`) and processed via PySide6 native event filtering with Shiboken `VoidPtr` safety.
- **Interactive Global Shortcut Recorder**: Interactive 2-key and 3-key keycap pill recorder UI (`ShortcutRecorderWidget`) with collision detection, Win32 error feedback, and safe rollback.
- **Landscape Preferences UI**: Modern landscape settings window (`680x440` px) with persistent left navigation sidebar (`QListWidget`), 6 stacked pages (`QStackedWidget`), dark charcoal selected navigation panels with green indicator (removing focus outlines).
- **System Tray Integration**: In-memory vector tray icon, context menu ("Show/Hide MediaDock", "Media Source", "Settings..."), dynamic tooltips, and click activation handlers.
- **Single-Instance Protection**: Enforces single-process execution via local socket guard (`SingleInstanceGuard`), focusing active Dynamic Island on secondary launches.
- **Preferences & Persistence**: Manage preferences (`close_to_tray`, `start_hidden`, `always_on_top`, `remember_position`, `compact_mode`, `hotkeys/show_hide`, `hotkeys/play_pause`, `autostart`) via Qt `QSettings` and Windows Registry (`winreg`). Includes custom read-only `CollapseDelaySpinBox` with stacked `▲`/`▼` controls.
- **Audio Analysis & Real-Time Waveform Visualizer**: End-to-end real-time audio visualization pipeline (`WASAPILoopbackCapture` -> `AudioFrame` -> `AudioAnalyzer` -> `MediaCore` -> `ReactiveVisualizerWidget`). Renders anti-aliased waveform bars reacting strictly to system audio output, with zero artificial movement during silence or pause.
- **Standalone Packaging**: Bundles into a single executable (`dist/MediaDock.exe`) using PyInstaller.

---

## Current Status & Verification

- **Source Launch Status**: Verified (`python -m src.main` launches with zero errors).
- **Automated Test Suite**: **258 / 258 tests passing** (`10.61s`).
- **Codebase Integrity**: `git diff --check` cleanly verified.
- **Packaged Artifact Launch**: `dist/MediaDock.exe` (verified running actively in background with pixel-perfect top-center geometry, preferences persistence, and metadata alignment).

---

## Documentation Links

- [**Technical Architecture Manual**](docs/architecture.md) — Comprehensive technical reference, component diagrams, signal flows, and OS integration details.
- [**User & Operations Guide**](docs/user_guide.md) — Detailed installation, configuration, global hotkeys, and troubleshooting guide.
- [**Project Bible**](PROJECT_BIBLE.md) — Core project vision, roadmap, V1 target specifications, and design philosophy.
- [**Project Status**](PROJECT_STATUS.md) — Milestone tracking, prototype matrix, and release status.

---

## Development Setup

1. **Clone Repository & Setup Virtual Environment**:
   ```cmd
   git clone https://github.com/YourUsername/SpotifyProject_OOC1.git
   cd SpotifyProject_OOC1
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

3. **Run Application**:
   ```cmd
   python -m src.main
   ```

---

## Testing & Build Commands

- **Run Automated Test Suite** (254 unit & integration tests):
  ```cmd
  python -m unittest discover -s tests
  ```

- **Check Codebase Whitespace & Formatting**:
  ```cmd
  git diff --check
  ```

- **Build Standalone Executable (`dist/MediaDock.exe`)**:
  ```cmd
  python scripts/build.py
  ```
