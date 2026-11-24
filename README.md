# MediaDock

**MediaDock** is a native Windows desktop media application built with **Python 3.14**, **PySide6 (Qt for Python)**, and **PyWinRT**. It automatically detects and controls system-wide media playback (Spotify, YouTube, VLC, Apple Music, Chrome/Edge) using the Windows **Global System Media Transport Controls (GSMTC)** API and presents a top-center **Dynamic Island** overlay.

---

## 1. Product Definition & Core Identity

- **Executable Name**: `MediaDock.exe`
- **Platform**: Windows 10 / 11 (64-bit)
- **Target Audience**: Windows desktop users desiring non-intrusive, ambient, universal media controls.

MediaDock runs as a lightweight, background desktop utility that monitors system-wide audio and media playback in real-time. It stays silently hidden when no media is active and automatically presents a sleek top-center collapsed capsule when media playback is detected. When hovered, the capsule seamlessly expands into an interactive media card allowing users to view metadata (track title, artist, album art) and issue media commands (play/pause, skip, volume adjustment, mute) without disrupting desktop workflows.

### Universal Scope
MediaDock integrates with any media application exposing the Windows GSMTC API:
- **Spotify** (primary visual design target)
- **Web Browsers** (Google Chrome, Microsoft Edge, Firefox, Brave — YouTube, SoundCloud, web audio)
- **VLC Media Player**
- **Apple Music**
- Other GSMTC-compliant desktop and web media players

---

## 2. Product Vision & Visual Design Language

- **Fixed System Visual Identity**: Pure Black (`#000000`) background and border, dark charcoal (`#141414` – `#222222`) secondary surfaces, subtle dark gray (`#2A2A2A`) borders, white (`#FFFFFF`) primary text, and muted gray (`#8A8A8A`) secondary text.
- **Status Indicators**:
  - **ACTIVE / PLAYING**: Spring Green (`#00FF7F`)
  - **INACTIVE / PAUSED / STOPPED / CLOSED**: Crimson Red (`#C1121C`)
- **Non-Customizable Product Colors**: The Dynamic Island background (`#000000`), border (`#000000`), and status dot colors are fixed by the product visual identity.
- **Silent Background Operation**: Starts with Windows (or on demand) silently in the background, listening for media sessions without requiring user intervention.

---

## 3. Top-Center Notch Screen Architecture & State Model

MediaDock presents a top-center, non-draggable overlay anchored flush against the top edge of the primary monitor (`y = 0`), styled as a sleek native display notch.

```
                    ┌──────────────┐
                    │    HIDDEN    │  (No Active Media / Disabled in Settings)
                    └──────┬───────┘
                           │
                     Media detected
                           │
                           ▼
              ┌──────────────────────────┐  (Flush with top screen bezel)
              │     COLLAPSED NOTCH      │  (Top-Center Sleek Notch 180x40 px)
              │ [Icon] Title — Artist  ● │  (Flat top edge, rounded bottom)
              └────────────┬─────────────┘
                           │
                       Mouse hover
                           │
                           ▼
              ┌──────────────────────────┐
              │      EXPANDED NOTCH      │  (Interactive Media Card 360x160 px)
              │  [Art] Meta / Controls   │  (Drop-down card from top bezel)
              └────────────┬─────────────┘
                           │
                    Mouse leaves
                           │
                   Collapse Delay (ms)
                           │
                           ▼
              ┌──────────────────────────┐
              │     COLLAPSED NOTCH      │
              └──────────────────────────┘
```

- **Symmetrical Geometry Morphing**: Smooth 180ms `OutCubic` geometry animation expanding downward from the top bezel and contracting symmetrically around a constant center X coordinate (`180x40` notch $\leftrightarrow$ `360x160` expanded card) with zero position drift across repeated hover cycles.
- **Hover Expansion & Inactivity Collapse**: Mouse hover on the notch immediately triggers downward expansion; mouse leave starts a configurable single-shot timer (default `3500ms`, adjustable 500–30000ms in settings) before auto-collapsing.
- **Notch Source Classification**: Dynamically identifies the active source app and renders crisp vector icons (`spotify.svg`, `youtube.svg`, `vlc.svg`, or `default_media.svg`) alongside elided track metadata.

---

## 4. Key Systems & Architecture

### 4.1 Media Engine & GSMTC Integration (`src/media/`, `src/core/`)
- **`MediaCore`**: Thread-safe Qt facade coordinating playback status, track metadata, audio analysis, and volume changes.
- **`GSMTCProvider`**: WinRT async listener enumerating system media sessions, extracting album art thumbnails, and auto-falling back across sessions.
- **`WindowsVolumeProvider`**: Direct Windows CoreAudio (`IAudioEndpointVolume` via ctypes COM) master volume and mute control with graceful degradation when audio endpoints are unavailable.

### 4.2 WASAPI Loopback Capture, Audio Equalizer & Real-Time Visualizer
- **`WASAPILoopbackCapture`**: Native COM loopback audio capture stream reading real PCM audio frames from the default Windows render endpoint.
- **`EqualizerAPOManager`**: Windows system-wide parametric equalizer and volume boost bridge (`mediadock_eq.txt` synchronizer) providing:
  - **Audio Boost (Preamp)**: Up to `+12.0 dB` volume boost beyond standard 100% Windows ceiling.
  - **Quick Tone Controls**: Bass low-shelf (`-12 dB` to `+12 dB`), Vocal Clarity peaking, Treble/Air high-shelf, and Noise Gate threshold (`0%` to `50%`).
  - **5-Band Graphic Equalizer**: Precision sliders for `60 Hz`, `250 Hz`, `1 kHz`, `4 kHz`, `16 kHz` with 6 factory presets (*Flat*, *Bass Boost*, *Vocal Clarity*, *Electronic*, *Rock*, *Acoustic*) and Flat reset.
- **Dynamic Visualizer Coupling**: `AudioAnalyzer` dynamically couples the active EQ and boost settings to the visualizer bars — boosting bass directly makes the bass bars bounce higher, increasing preamp boost scales overall visual sensitivity, and the noise gate silences low-level background hiss.
- **`ReactiveVisualizerWidget`**: Anti-aliased rounded waveform bars reacting strictly to system audio output, resting at a clean static baseline during silence or pause (zero artificial movement).

### 4.3 Win32 Global Shortcuts & Recorder
- **OS-Wide Hotkey Dispatch**: Registered directly with the window HWND via Win32 `RegisterHotKey`:
  - **Show / Hide MediaDock**: `Ctrl+Alt+S`
  - **Toggle Play / Pause**: `Ctrl+Alt+Space`
- **Native Event Filtering**: `HotkeyNativeEventFilter` intercepts `WM_HOTKEY` (0x0312) messages safely handling PySide6 Shiboken `VoidPtr` objects.
- **Interactive Shortcut Recorder**: `ShortcutRecorderWidget` in settings captures keyboard input directly with strict 2-key and 3-key rules, duplicate assignment detection, and automatic rollback if OS registration fails.

### 4.4 Landscape Preferences UI & Persistence
- **Modern Landscape Dialog**: `680x440` px window with a 160px persistent left navigation sidebar and 6 stacked pages:
  1. **Preferences**: Close to tray, Start minimized, Start with Windows (Registry `HKCU\...Run`), Always on Top, Enable Dynamic Island.
  2. **Global Shortcuts**: Interactive shortcut recorders for Show/Hide and Play/Pause.
  3. **Dynamic Island**: Configurable collapse delay via `CollapseDelaySpinBox` (500–30000 ms).
  4. **Appearance**: Fixed system visual identity overview.
  5. **Audio**: Equalizer APO status, Audio Boost (Preamp), tone controls (bass, clarity, treble, noise gate), and 5-band graphic equalizer with presets.
  6. **About**: Version information and architectural summary.
- **`SettingsManager`**: Backed by Qt `QSettings` INI storage with explicit synchronization on save and system tray exit.
- **Single-Instance Protection**: Enforced via `SingleInstanceGuard` local socket IPC, ensuring only one instance runs and restoring the existing window on secondary launches.

---

## 5. Development & Testing

### Prerequisites
- Windows 10 or Windows 11
- Python 3.10+ (Python 3.14 recommended)

### Setup Virtual Environment
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run Application from Source
```cmd
python -m src.main
```

### Run Automated Test Suite
MediaDock includes a comprehensive unit and integration test suite (275 tests covering core models, state machine, audio analysis, hotkeys, Equalizer APO, and widget lifecycle):
```cmd
.venv\Scripts\python.exe -m unittest discover -s tests
```

### Check Whitespace & Formatting
```cmd
git diff --check
```

### Build Standalone Executable
PyInstaller compiles MediaDock into a single standalone executable with all assets bundled:
```cmd
.venv\Scripts\python.exe scripts/build.py
```
Output artifact: `dist/MediaDock.exe`.

---

## 6. Implementation Status & Milestones

### Completed Milestones Summary
- **Milestone 1 — Foundation (COMPLETE)**: `FramelessWindow`, `MainWindow`, PySide6 entry point.
- **Milestone 2 — Windows Media Detection (COMPLETE)**: `BaseMediaProvider`, `GSMTCProvider`, `MediaCore`, PyWinRT session listening, metadata extraction.
- **Milestone 3 — Connected UI & Advanced Controls (COMPLETE)**: Transport control abstraction, GSMTC async dispatches, `MediaCore` routing, interactive controls, seeking state machine.
- **Milestone 4 — Visual Polish & Dynamic Styling (COMPLETE)**: Product design tokens, QSS styling, `ElidedLabel`, status badges, opacity animations, album-art color extraction.
- **Milestone 5 — System Tray & Settings (COMPLETE)**: `SettingsManager`, `SystemTrayIcon`, `SettingsDialog`, lifecycle integration.
- **Milestone 6 — Advanced Features, OS Integration & Packaging (COMPLETE)**: Windows Autostart (`AutostartManager`), Global Hotkeys (`GlobalHotkeyManager`), PyInstaller spec (`MediaDock.spec`), documentation suite (`docs/architecture.md`, `docs/user_guide.md`).
- **Milestone 7 — Media Source & Control Expansion (COMPLETE)**: GSMTC multi-session selection (`MediaSessionInfo`), master volume & mute control (`WindowsVolumeProvider`, CoreAudio `IAudioEndpointVolume` COM integration), configurable global hotkeys.
- **Phase 8 — Reliability, Single-Instance Guard & Desktop Lifecycle (COMPLETE)**: Single-instance application lock (`SingleInstanceGuard`), process/window lifecycle decoupling, clean system tray exit, autostart verification (**155 / 155 tests passing**).
- **Phase 9.1 — Dynamic Island Foundation (COMPLETE)**: Symmetrical geometry morphing, `OutCubic` animations, state machine (**182 / 182 tests passing**).
- **Phase 9.2 — V1 Core Refinements & Launch Bugfix (COMPLETE)**: Resolved launch bug, Win32 hotkeys, fixed visual identity, landscape settings.
- **Phase 9.2.4A — WASAPI Loopback Capture Layer (COMPLETE)**: Native Windows loopback capture (`WASAPILoopbackCapture` / `AudioFrame`) (**213 / 213 tests passing**).
- **Phase 9.2.4B — Audio Analysis Engine (COMPLETE)**: Time-domain sub-window RMS energy engine (`AudioAnalyzer`), multi-channel downmixing, attack/decay smoothing, normalized bar heights `0.0`–`1.0` (**241 / 241 tests passing**).
- **Phase 9.2.4C — Audio Visualizer UI Integration & WASAPI Wiring (COMPLETE)**: End-to-end real-audio visualizer pipeline (`WASAPILoopbackCapture` -> `AudioAnalyzer` -> `MediaCore` -> `MainWindow` -> `ReactiveVisualizerWidget`), strictly real audio with zero artificial movement (**246 / 246 tests passing**).
- **Bug Fix & Polish Milestone (COMPLETE)**: Resolved Preference Persistence Regression, Collapse Delay Control UI (`CollapseDelaySpinBox`), Notch Metadata Center Alignment, and Geometry Lifecycle Initial Launch Centering (**256 / 256 tests passing**).
- **V1 Final Core Issues Fix Milestone (COMPLETE)**: Resolved Preferences Persistence on System Tray Exit, Collapsed Metadata Vertical Alignment Post-Collapse, and Collapsed to Expanded Animation Direction (**258 / 258 tests passing**).
- **Documentation Consolidation Milestone (COMPLETE)**: Filtered noise, merged `PROJECT_BIBLE.md` and `README.md` into a single authoritative `README.md`, updated `AI_RULES.md`, and eliminated redundant specification documents (**258 / 258 tests passing**).
- **Audio Boost & Equalizer Milestone (COMPLETE)**: Implemented `EqualizerAPOManager`, Preamp Volume Boost (up to +12 dB), Bass low-shelf, Vocal Clarity peaking, Treble high-shelf, Noise Gate threshold, 5-band Graphic Equalizer with presets (Flat, Bass Boost, Vocal Clarity, Electronic, Rock, Acoustic, Custom), and dynamic coupling to `AudioAnalyzer` for real-time visualizer bar reactions (**275 / 275 tests passing**).
- **Notch Screen Conversion Milestone (COMPLETE)**: Converted floating capsule into flush top-center **Notch Screen** (`y = 0`, flat top against screen bezel, smooth rounded bottom corners), updated `CollapsedNotchWidget`, `FramelessWindow`, and `MainWindow` geometry lifecycle (**275 / 275 tests passing**).
- **V1.5 Visual, Audio & Desktop Superpowers Milestone (COMPLETE)**: Implemented all 11 core upgrades in one go:
  1. *Dynamic Album Art Color Glow*: Radial ambient glow and accent tinting from track artwork.
  2. *Interactive Progress Scrubbing*: `InteractiveScrubSlider` with proportional click-to-seek, smooth scrubbing, and live timestamp tooltip.
  3. *Mirrored Waveform Visualizer*: Symmetrical vertical bar expansion around center baseline with rounded pill caps.
  4. *Click vs. Hover Trigger Mode*: Configurable expansion trigger with intent delay deadzone timer.
  5. *Shuffle & Repeat Playback Toggles*: WinRT GSMTC controls with dedicated SVG vector icons.
  6. *Fullscreen Game & App Auto-Hide*: Native Win32 foreground window detection suppressing overlay in games/movies.
  7. *Multi-Monitor Display Selector*: Configurable monitor target anchoring across multi-screen setups.
  8. *True FFT Audio Spectrum*: Pure Python Radix-2 FFT logarithmic spectrum analysis (30Hz–16000Hz).
  9. *Per-App Volume Mixing*: Application-targeted volume adjustment with master volume fallback.
  10. *Multi-Session Media Switcher Pill*: Dynamic session switcher dropdown in expanded card.
  11. *Live Synchronized Lyrics Preview*: Async LRCLIB lyrics client and live timeline-synced lyric line.
  (**286 / 286 tests passing**).

### Implemented Codebase vs Target Specification Matrix

| Feature / Component | Current Implementation Codebase | Target V1 Specification Status |
| :--- | :--- | :--- |
| **Application Launch Stability** | Verified (`python -m src.main` and `dist/MediaDock.exe` launch with 0 errors) | Complete |
| **Top-Center Notch Screen** | Implemented (Flush `y = 0` at top bezel, flat top, rounded bottom corners, 180x40 notch) | Complete |
| **Dynamic Album Art Glow** | Implemented (Ambient radial gradient glow, tinted visualizer, and accent highlights) | Complete |
| **Interactive Progress Scrubbing** | Implemented (`InteractiveScrubSlider` click-to-seek, smooth drag, live timestamp tooltip) | Complete |
| **Mirrored Waveform Visualizer** | Implemented (`ReactiveVisualizerWidget(mirrored=True)` symmetrical vertical bar expansion) | Complete |
| **Click vs. Hover Trigger Mode** | Implemented (Configurable hover/click trigger with hover intent delay timer in Settings) | Complete |
| **Shuffle & Repeat Toggles** | Implemented (GSMTC async dispatches, `shuffle.svg` / `repeat.svg`, interactive buttons) | Complete |
| **Fullscreen Game Auto-Hide** | Implemented (`is_foreground_fullscreen` Win32 detection, auto-hide/restore overlay) | Complete |
| **Multi-Monitor Display Selector** | Implemented (Settings monitor selector, multi-screen geometry anchoring) | Complete |
| **True FFT Audio Spectrum** | Implemented (`AudioAnalyzer` pure-Python Cooley-Tukey Radix-2 FFT logarithmic spectrum) | Complete |
| **Per-App Volume Mixing** | Implemented (`set_app_volume` CoreAudio interface with master fallback) | Complete |
| **Multi-Session Media Switcher** | Implemented (Active session dropdown in expanded card, dynamic `sessions_changed` sync) | Complete |
| **Live Synchronized Lyrics** | Implemented (`LyricsProvider` async LRCLIB integration, LRC timestamp matching) | Complete |
| **Geometry Lifecycle & Centering** | Fixed & Verified (Initial launch & 10+ expand/collapse cycles hold exact center X alignment) | Complete |
| **Preference Persistence Lifecycle** | Fixed & Verified (Preferences refresh on open, sync on tray exit, QSettings preserved) | Complete |
| **Notch Metadata Alignment** | Fixed & Verified (Metadata content group horizontally CENTER and vertically MIDDLE in 180x40 notch) | Complete |
| **Symmetrical Expand Direction** | Fixed & Verified (Expansion originates from centered notch, center X = 960 strictly constant) | Complete |
| **Live Media Source Icons** | Implemented (Spotify desktop/Store, VLC, YouTube metadata validation, `default_media.svg` fallback) | Complete |
| **WASAPI Loopback Capture** | Implemented (`WASAPILoopbackCapture` native COM loopback capture, zero micro-dependency) | Complete |
| **Equalizer APO Integration** | Implemented (`EqualizerAPOManager` detection, config generation, `mediadock_eq.txt` sync) | Complete |
| **Audio Boost & Tone Controls** | Implemented (Preamp boost to +12 dB, Bass low-shelf, Clarity peaking, Treble air, Noise Gate) | Complete |
| **5-Band Graphic Equalizer** | Implemented (60Hz, 250Hz, 1kHz, 4kHz, 16kHz sliders, 6 presets, Flat reset) | Complete |
| **Global Win32 Hotkey Dispatch** | Implemented (HWND message target, Shiboken VoidPtr fix, `Ctrl+Alt+S` / `Ctrl+Alt+Space`) | Complete |
| **Global Shortcut Recorder UI** | Implemented (`ShortcutRecorderWidget` interactive keycap pills with `+` labels, 2/3-key validation, rollback) | Complete |
| **Landscape Settings UI & Sidebar** | Implemented (`680x440` px window, 160px sidebar, 6 pages, dark charcoal selected panel, no focus outline) | Complete |
| **Fixed Visual Identity System** | Implemented (Pure Black `#000000` BG/border, `#00FF7F` active green, `#C1121C` inactive red, non-customizable product colors) | Complete |

### Verification & Release Summary
- **Source Launch Status**: `python -m src.main` -> **SUCCESSFUL**
- **Automated Test Suite**: **286 / 286 tests passing** cleanly (`.venv\Scripts\python.exe -m unittest discover -s tests`).
- **Whitespace & Formatting**: `git diff --check` clean (0 errors).
- **Standalone Executable Build**: `MediaDock.spec` PyInstaller build completed cleanly (`dist/MediaDock.exe`).

---

## 7. Multi-Phase Roadmap

- **V1 (Current Baseline - Complete)**:
  - Top-Center Notch Screen (`180x40` notch flush at `y = 0`) and expanded card (`360x160`).
  - Symmetrical 180ms `OutCubic` morphing with zero position drift.
  - GSMTC universal media detection & multi-session support.
  - CoreAudio master volume & mute integration.
  - WASAPI loopback audio capture & real-time RMS waveform visualizer.
  - Equalizer APO integration: Audio boost (+12 dB preamp), quick tone controls, and 5-band graphic EQ with dynamic visualizer coupling.
  - Win32 global hotkeys with interactive 2/3-key recorder UI.
  - Landscape settings window and system tray lifecycle.
  - Single-instance IPC guard and autostart integration.
  - Complete 275/275 test coverage and standalone PyInstaller build.

- **V1.5 (Planned Polish)**:
  - Mirrored waveform visualizer (symmetrical vertical expansion, higher bar density).
  - Audio visualizer attack/decay tuning sliders in Settings.
  - Expand trigger customization (hover vs. click-to-expand).

- **V2 (Advanced Desktop Integration)**:
  - Full-screen app and game auto-hide detection (preventing overlay above games/presentations).
  - Multi-monitor support (monitor selection or follow-active-cursor monitor).
  - Dynamic album-art dominant color extraction for visualizer and accent highlights.
  - Per-application volume control via CoreAudio `IAudioSessionControl2`.

- **V3 (Extended Capabilities)**:
  - Real-time multi-band FFT audio spectrum analysis (bass, mid, treble separation).
  - Synchronized / plain lyrics integration.
  - Shuffle and repeat playback toggles.

---

## 8. Documentation Index

- [**Technical Architecture Manual**](docs/architecture.md) — Comprehensive technical reference, component diagrams, signal flows, and OS integration details.
- [**User & Operations Guide**](docs/user_guide.md) — User setup, shortcuts, and operation details.
