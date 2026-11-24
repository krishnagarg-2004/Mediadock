# MediaDock User & Operation Guide

Welcome to **MediaDock**! This guide covers installing, configuring, and operating MediaDock on Windows.

---

## 1. Prerequisites & System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit, required for WinRT GSMTC API, WASAPI loopback audio capture, and CoreAudio volume control).
- **Python**: Python 3.10+ (Python 3.14 recommended) when running from source code.
- **Dependencies**: Listed in [requirements.txt](../requirements.txt):
  - `PySide6>=6.6.0`
  - `winrt-Windows.Foundation>=3.0.0`
  - `winrt-Windows.Media.Control>=3.0.0`
  - `winrt-Windows.Storage.Streams>=3.0.0`
  - `pyinstaller>=6.0.0`
- **Optional System Equalizer**: Install **Equalizer APO** if you want real-time system-wide preamp volume boost (+12 dB) and parametric EQ applied to Windows audio output. Even without Equalizer APO, MediaDock's EQ sliders dynamically react with the notch visualizer bars.

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

### 3.1 Top-Center DeskNotch Interface
MediaDock anchors flush against the top edge of your screen (`y = 0`) and remains hidden until an active media session (Spotify, Chrome/YouTube, Edge, VLC, etc.) is detected:

- **Collapsed Slim Notch (`220×34` px)**:
  - Displays rounded miniature album artwork (or source vector icon), elided track title, a 3-bar reactive pulse, a 12-hour tabular clock, and a status indicator dot (`#00FF7F` playing / `#C1121C` paused).
- **Expanded Frosted Card (`380×174` px)**:
  - Hover over (or click, depending on your trigger setting) the notch to expand smoothly downward into the frosted card with an ambient cover-art glow:
    - **Play / Pause**: Click the central solid white circular play/pause disc.
    - **Previous / Next / Shuffle / Repeat**: Full transport controls alongside the mirrored reactive spectrum visualizer.
    - **Volume & Mute**: Adjust volume or click the speaker button to mute.
    - **Interactive Progress Scrubbing**: Click anywhere or drag along the progress bar (with live timestamp tooltip) to seek to that timestamp.
    - **Multi-Session Switcher**: When multiple players are active at once, use the header dropdown pill to switch which app MediaDock controls.
    - **Live Synchronized Lyrics**: View time-synced lyric lines (`♪ ...`) beneath the artist name when enabled.
    - **Pin / Lock (`🔓`/`🔒`) & Settings (`⚙`) Dock**: Pin the notch open so it stays visible after moving the cursor away, or open Settings in one click.

### 3.2 System Tray Operation
MediaDock runs in the Windows System Tray (notification area):
- **Tooltip**: Displays current track title, artist, and playback state.
- **Media Source Selection Submenu**: Lists active media sessions (`Spotify`, `Google Chrome`, `VLC`, etc.) to switch focus.
- **Left-Click / Right-Click**: Toggle visibility, jump to Preferences, or quit cleanly.

---

## 4. Preferences, Equalizer & Global Hotkeys

Open **Settings** via the notch gear button or by right-clicking the System Tray icon:

- **Preferences**: Close to tray, Start minimized, Start with Windows, Always on Top, Enable Dynamic Island, Auto-Hide in Fullscreen Games & Apps, Live Synchronized Lyrics, and Target Display Monitor.
- **Global Shortcuts**: Customize OS-wide shortcuts for **Show/Hide MediaDock** (default: `Ctrl+Alt+S`) and **Toggle Play/Pause** (default: `Ctrl+Alt+Space`).
  - Supports 2-key or 3-key combinations (`Ctrl`, `Alt`, `Shift`, `Win` + `A-Z`, `0-9`, `Space`, `Tab`, `Return`, `F1-F24`).
- **Dynamic Island**: Configure **Expansion Trigger** (*Hover to Expand* or *Click to Expand*), **Hover Intent Delay** (`0–1000 ms`), and **Collapse Delay** (`500–30000 ms`).
- **Audio & Equalizer**: Choose **Visualizer Spectrum Mode** (*True FFT Frequency Spectrum* or *Time-Domain RMS Energy*), adjust Preamp Volume Boost (`0` to `+12 dB`), Bass/Clarity/Treble tone controls, Noise Gate (`0%–50%`), and the 5-band graphic EQ with presets.

---

## 5. Known Limitations & Fallbacks

- **Headless / Virtualized Audio**: In environments without active CoreAudio volume endpoints, volume controls degrade gracefully while media detection and playback transport remain functional.
- **Hotkey Conflicts**: If another application already claims a shortcut combination, MediaDock reports an error and safely rolls back to your previous working shortcuts.
