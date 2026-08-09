# MediaDock

**MediaDock** is a native Windows floating media dock application built with **Python 3.14**, **PySide6 (Qt for Python)**, and **PyWinRT**. It automatically detects and controls system-wide media playback (Spotify, YouTube, VLC, Apple Music, Chrome/Edge) using the Windows **Global System Media Transport Controls (GSMTC)** API.

---

## Key Features

- **Universal Windows Media Detection**: Automatically detects active media sessions across Spotify, web browsers, and local media players via WinRT GSMTC.
- **Frameless Floating Dock**: Smooth rounded frameless window with desktop click-and-drag movement and Catppuccin Mocha visual styling.
- **Dynamic Accent Glow**: Extracts dominant colors from album artwork to dynamically tint the widget background glow.
- **Interactive Controls & Progress Seeking**: Play, pause, skip, and scrub track progress via slider seeking.
- **System Tray Integration**: In-memory vector tray icon, context menu, dynamic tooltips, and click activation handlers.
- **Global OS Shortcuts**: Control playback globally from anywhere on Windows using `Ctrl+Alt+M` (Show/Hide) and `Ctrl+Alt+Space` (Play/Pause).
- **Settings Persistence**: Manage preferences (`close_to_tray`, `start_hidden`, `always_on_top`, `remember_position`, `autostart`) via Qt `QSettings` and Windows Registry (`winreg`).
- **Standalone Packaging**: Bundles into a single executable (`dist/MediaDock.exe`) using PyInstaller.

---

## Documentation Links

- [**Technical Architecture Manual**](docs/architecture.md) — Comprehensive technical reference, component diagrams, signal flows, and OS integration details.
- [**User & Operations Guide**](docs/user_guide.md) — Detailed installation, configuration, global hotkeys, and troubleshooting guide.
- [**Project Bible**](PROJECT_BIBLE.md) — Core project vision, roadmap, and design philosophy.
- [**Project Status**](PROJECT_STATUS.md) — Milestone tracking and task completion status.

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

- **Run Automated Test Suite** (111 unit & integration tests):
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

---

## Current Project Status

- **Milestone 1 — Foundation**: COMPLETE
- **Milestone 2 — Windows Media Detection**: COMPLETE
- **Milestone 3 — Connected UI & Advanced Controls**: COMPLETE
- **Milestone 4 — Visual Polish & Dynamic Styling**: COMPLETE
- **Milestone 5 — System Tray & Settings**: COMPLETE
- **Milestone 6 — Advanced Features, OS Integration & Packaging**: IN PROGRESS (Steps 1–3 Complete; Step 4 Documentation in review)
