# MediaDock User & Operation Guide

Welcome to **MediaDock**! This document provides instructions for installing, configuring, operating, and building MediaDock on Windows.

---

## 1. Prerequisites & System Requirements

- **Operating System**: Windows 10 or Windows 11 (required for WinRT Global System Media Transport Controls API).
- **Python**: Python 3.14 (or Python 3.10+) when running from source code.
- **Dependencies**: Listed in [`requirements.txt`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/requirements.txt):
  - `PySide6>=6.6.0`
  - `winrt-Windows.Foundation>=3.0.0`
  - `winrt-Windows.Media.Control>=3.0.0`
  - `winrt-Windows.Storage.Streams>=3.0.0`
  - `pyinstaller>=6.0.0`

---

## 2. Installation & Development Setup

### Running from Source
1. Clone the repository:
   ```cmd
   git clone https://github.com/YourUsername/SpotifyProject_OOC1.git
   cd SpotifyProject_OOC1
   ```
2. Create and activate a virtual environment:
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
4. Launch MediaDock:
   ```cmd
   python -m src.main
   ```

---

## 3. Using MediaDock

### 3.1 Floating Dock Window
- **Playback Controls**:
  - **Play / Pause**: Click the central play/pause toggle button.
  - **Previous Track**: Click the left arrow button.
  - **Next Track**: Click the right arrow button.
- **Progress & Seeking**:
  - Drag the progress slider to scrub to a specific position in the current track. Releasing the mouse executes the seek command via GSMTC.
- **Dragging**: Click and hold anywhere on the frameless window background to move MediaDock around your desktop screen.

### 3.2 System Tray Operation
MediaDock runs in the Windows System Tray (notification area at the bottom-right of your screen):
- **Tray Icon**: Displays a dark badge with a `♪` glyph.
- **Tooltip**: Hover over the tray icon to view the current track title, artist, and playback state (`"MediaDock - Track by Artist [PLAYING]"`).
- **Left-Click (Trigger)**: Toggles window visibility (Show/Hide).
- **Double-Click**: Restores and brings MediaDock to the front.
- **Right-Click Context Menu**:
  - `Show MediaDock` / `Hide MediaDock`: Toggles window visibility.
  - `Settings...`: Opens the Preferences configuration dialog.
  - `Exit MediaDock`: Cleanly stops background listeners and terminates the application.

---

## 4. Settings & Configuration

Access the Settings dialog by right-clicking the system tray icon and selecting **Settings...**.

| Preference Setting | Description | Default |
|---|---|---|
| **Close to system tray** | Closing the window hides MediaDock to the system tray instead of exiting. | Enabled (`True`) |
| **Start hidden in system tray** | Application launches minimized in the system tray without popping up the main window. | Disabled (`False`) |
| **Always on top** | Keeps the floating dock window pinned on top of other desktop windows. | Enabled (`True`) |
| **Remember window position** | Saves the last desktop screen position and restores it on next launch. | Enabled (`True`) |
| **Start with Windows** | Configures Windows Registry (`HKCU\...\Run`) to launch MediaDock automatically on system boot. | Disabled (`False`) |

---

## 5. Global Keyboard Shortcuts

MediaDock registers system-wide OS hotkeys using the Win32 API, allowing you to control playback even when MediaDock or media players are unfocused or minimized:

- **`Ctrl + Alt + M`**: Toggle MediaDock window visibility (Show / Hide).
- **`Ctrl + Alt + Space`**: Toggle Play / Pause on the active system media session.

---

## 6. Packaging & Standalone Executable

You can build a standalone executable that runs on Windows without requiring a Python installation:

1. Run the build wrapper script:
   ```cmd
   python scripts/build.py
   ```
2. The script will clean old build outputs, invoke PyInstaller with [`MediaDock.spec`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/MediaDock.spec), and produce:
   ```
   dist/MediaDock.exe
   ```
3. Launch `dist/MediaDock.exe` directly or run with command-line flags:
   ```cmd
   dist\MediaDock.exe --minimized
   ```

---

## 7. Troubleshooting & Known Limitations

- **No Media Detected ("No Media Playing")**:
  - Ensure a GSMTC-compliant media application is actively running (e.g. Spotify desktop, YouTube in Chrome/Edge, VLC, Apple Music).
  - Web browsers must have media playback actively playing audio for Windows GSMTC to expose the session.
- **Global Hotkey Conflicts**:
  - If another application has already registered `Ctrl+Alt+M` or `Ctrl+Alt+Space`, MediaDock will log a warning and continue running without capturing that specific hotkey combination.
- **Standalone Executable Smoke Testing Note**:
  - The standalone executable build (`dist/MediaDock.exe`) is programmatically verified for process launch, memory health, and CLI flag handling. Interactive visual desktop smoke tests (such as live tray icon rendering and mouse clicks) are manually verified on a physical Windows monitor screen.
