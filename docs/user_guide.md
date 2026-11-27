# MediaDock User & Operation Guide

Welcome to **MediaDock**! This guide covers installing, configuring, and operating MediaDock on Windows.

---

## 1. Prerequisites & System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit, required for WinRT GSMTC API, WASAPI loopback audio capture, and CoreAudio volume control).
- **Python**: Python 3.10+ (Python 3.14 recommended) when running from source code.
- **Dependencies**: Listed in [requirements.txt](../requirements.txt):
  - `PySide6>=6.6.0`
  - `winrt-Windows.Foundation>=3.0.0,<4.0.0`
  - `winrt-Windows.Media>=3.0.0,<4.0.0`
  - `winrt-Windows.Media.Control>=3.0.0,<4.0.0`
  - `winrt-Windows.Storage.Streams>=3.0.0,<4.0.0`
  - `pyinstaller>=6.0.0`
- **Optional System Equalizer**: MediaDock prompts once on startup (or via **Settings → Audio & Equalizer → Allow & Connect Audio...**) for permission to install/configure **Equalizer APO** so Preamp Boost (`+12 dB`), Tone sliders, and the 5-band EQ apply directly to your speakers/headphones as well as the notch visualizer.

---

## 2. Installation & Development Setup

### Running from Source
1. Clone the repository:
   ```cmd
   git clone https://github.com/krishnagarg-2004/Mediadock.git
   cd Mediadock
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

### 3.1 Top-Center Notch & Oval Interface
MediaDock stays hidden until an active media session (Spotify, Chrome/YouTube, Edge, VLC, etc.) is detected, then presents a hybrid top-center overlay:

- **Collapsed Slim Notch (`220×34` px)**:
  - Anchored flush against the top screen bezel (`y = 0`) with `8px` flared top ears and `14px` bottom corners. Displays rounded miniature album artwork (or source vector icon), elided track title, a 3-bar reactive pulse, and a 12-hour tabular clock.
- **Expanded Oval Frosted Card (`410×178` px, or `410×216` px with lyrics)**:
  - Hover over (or click, depending on your trigger setting) the notch to expand smoothly downward into a floating oval card (`y = 12`, `32px` corners) with an ambient cover-art glow:
    - **Play / Pause**: Click the central solid white circular play/pause disc.
    - **Previous / Next / Shuffle / Repeat**: Full transport controls alongside the mirrored reactive spectrum visualizer.
    - **Volume & Mute**: Adjust volume or click the speaker button to mute.
    - **Interactive Progress Scrubbing**: Click anywhere or drag along the progress bar (with live timestamp tooltip) to seek to that timestamp.
    - **Multi-Session Switcher**: When multiple players are active at once, use the header dropdown pill to switch which app MediaDock controls.
    - **Live Synchronized Lyrics**: View time-synced lyric lines (`♪ ...`) in a dedicated full-width strip underneath the media tile when enabled.
    - **Pin / Lock (`🔓`/`🔒`) & Settings (`⚙`) Dock**: Pin the notch open so it stays visible after moving the cursor away, or open Settings in one click.

### 3.2 System Tray Operation
MediaDock runs in the Windows System Tray (notification area):
- **Tooltip**: Displays current track title, artist, and playback state.
- **Media Source Selection Submenu**: Lists active media sessions (`Spotify`, `Google Chrome`, `VLC`, etc.) to switch focus.
- **Left-Click / Right-Click**: Toggle visibility, jump to Preferences, or quit cleanly.

---

## 4. Preferences, Appearance, Equalizer & Global Hotkeys

Open the frosted Gaussian-blur **Settings** window (`820×600` px) via the notch gear button or by right-clicking the System Tray icon:

- **Preferences**: Close to tray, Start minimized, Start with Windows, Always on Top, Enable Dynamic Island, Auto-Hide in Fullscreen Games & Apps, Live Synchronized Lyrics, and Target Display Monitor.
- **Global Shortcuts**: Customize OS-wide shortcuts for **Show/Hide MediaDock** (default: `Ctrl+Alt+S`) and **Toggle Play/Pause** (default: `Ctrl+Alt+Space`).
  - Supports 2-key or 3-key combinations (`Ctrl`, `Alt`, `Shift`, `Win` + `A-Z`, `0-9`, `Space`, `Tab`, `Return`, `F1-F24`).
- **Dynamic Island**: Configure **Expansion Trigger** (*Hover to Expand* or *Click to Expand*), **Hover Intent Delay** (`0–1000 ms`), and **Collapse Delay** (`500–30000 ms`).
- **Appearance**: Choose **Background Style** (*Solid Color*, *Gradient*, or *Custom Banner Image*), customize solid background & border `#RRGGBB` hex colors, pick from 8 gradient presets or custom 2/3-stop hex colors across 7 gradient styles (*Diagonal*, *Horizontal*, *Vertical*, *Reverse Diagonal*, *Radial*, *Conic Sweep*, *Mesh*), or select custom image banners (`PNG`, `JPG`, `WEBP`, `BMP`) separately for the **Expanded Card** and **Collapsed Notch** with crop focus, `0–85%` readability dim slider, and live dual Collapsed/Expanded previews.
- **Audio & Equalizer**: Choose **Visualizer Spectrum Mode** (*True FFT Frequency Spectrum* or *Time-Domain RMS Energy*), adjust Preamp Volume Boost (`0` to `+12 dB`), Bass/Clarity/Treble tone controls, Noise Gate (`0%–50%`), and the 5-band graphic EQ with presets.
- **About**: View version details, clickable GitHub repository/issue links, and runtime shortcut summary.

---

## 5. Known Limitations & Fallbacks

- **Headless / Virtualized Audio**: In environments without active CoreAudio volume endpoints, volume controls degrade gracefully while media detection and playback transport remain functional.
- **Hotkey Conflicts**: If another application already claims a shortcut combination, MediaDock reports an error and safely rolls back to your previous working shortcuts.
