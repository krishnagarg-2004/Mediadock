# MediaDock User & Operation Guide

Welcome to **MediaDock**! This document provides instructions for installing, configuring, operating, and building MediaDock on Windows.

---

## 1. Prerequisites & System Requirements

- **Operating System**: Windows 10 or Windows 11 (required for WinRT Global System Media Transport Controls API and CoreAudio volume control).
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
  - **Previous Track**: Click the left arrow button (`⏮`).
  - **Next Track**: Click the right arrow button (`⏭`).
- **Master Volume & Mute**:
  - **Volume Slider**: Drag the volume slider to adjust Windows master volume (0–100%).
  - **Mute Button**: Click the vector speaker button to mute or unmute master audio.
- **Progress & Seeking**:
  - Drag the timeline progress slider to scrub to a specific position in the current track. Releasing the mouse executes the seek command via GSMTC.
- **Compact View Mode**:
  - Toggle between Full Mode (360x140 px) and Compact Mode (240x48 px mini widget) by right-clicking the window and selecting **Compact Mode**, checking **Compact Mode View** in Preferences, or using the System Tray menu.
- **Desktop Edge Snapping**:
  - Drag MediaDock near any screen edge (within 15 px). MediaDock will automatically snap against the top, bottom, left, or right work-area boundary, respecting the Windows taskbar and multi-monitor setups.
- **Dragging**: Click and hold anywhere on the frameless window background to move MediaDock across your desktop screens.

### 3.2 System Tray Operation
MediaDock runs in the Windows System Tray (notification area at the bottom-right of your screen):
- **Tray Icon**: Displays a dark badge with a `♪` glyph.
- **Tooltip**: Hover over the tray icon to view the current track title, artist, and playback state (`"MediaDock - Track by Artist [PLAYING]"`).
- **Media Source Selection Submenu**: Hover over or click **Media Source** in the tray menu to view all active media sessions (`Spotify`, `Google Chrome`, `VLC`, `Microsoft Edge`) and switch active playback targets.
- **Left-Click (Trigger)**: Toggles window visibility (Show/Hide).
- **Double-Click**: Restores and brings MediaDock to the front.

---

## 4. Preferences & Global Hotkeys

Access the Preferences dialog by right-clicking the System Tray icon and selecting **Preferences...**:

- **Close to System Tray**: Hides MediaDock to the system tray when closing the window or pressing Escape.
- **Start Minimized to Tray**: Launches MediaDock hidden in the system tray on startup.
- **Start with Windows**: Automatically launches MediaDock when Windows boots.
- **Always on Top**: Keeps MediaDock floating above other desktop windows.
- **Remember Window Position**: Saves and restores screen coordinates across restarts.
- **Compact Mode View**: Displays the minimal 240x48 px widget view.
- **Global Shortcuts**: Customize OS-wide hotkeys for **Show/Hide** (default: `Ctrl+Alt+M`) and **Play/Pause** (default: `Ctrl+Alt+Space`).
  - Supported modifiers: `Ctrl`, `Alt`, `Shift`, `Win`.
  - Supported keys: `A-Z`, `0-9`, `Space`, `Tab`, `Return`, `Escape`, `F1-F24`.
  - If a shortcut is already in use by another application or missing a modifier, MediaDock displays an error and safely rolls back to your previous working shortcuts.

---

## 5. Known Limitations & Fallbacks

- **Headless / Virtualized Audio**: In virtual machines or headless environments without physical audio master volume endpoints, CoreAudio volume controls degrade gracefully by hiding the volume slider and mute button while keeping playback fully operational.
- **Hotkey Conflicts**: If another application registers a global shortcut before MediaDock, MediaDock prevents overwriting and retains your existing shortcut configuration.
