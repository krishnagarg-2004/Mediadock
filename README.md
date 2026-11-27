# MediaDock

**MediaDock** is a native Windows desktop media application built with **Python 3.14**, **PySide6 (Qt for Python)**, and **PyWinRT**. It automatically detects and controls system-wide media playback (Spotify, YouTube, VLC, Apple Music, Chrome/Edge) using the Windows **Global System Media Transport Controls (GSMTC)** API and presents a top-center **Dynamic Island** overlay.

---

## 1. Product Definition & Core Identity

- **Executable Name**: `MediaDock.exe`
- **Platform**: Windows 10 / 11 (64-bit)
- **Target Audience**: Windows desktop users desiring non-intrusive, ambient, universal media controls.

MediaDock runs as a lightweight, background desktop utility that monitors system-wide audio and media playback in real-time. It stays silently hidden when no media is active and automatically presents a sleek DeskNotch-styled top-center notch bar when media playback is detected. When triggered, the notch expands downward into an interactive frosted media card allowing users to view metadata (track title, artist, album art, live synchronized lyrics) and issue media commands (play/pause, skip, shuffle, repeat, interactive scrub seek, volume adjustment, mute) without disrupting desktop workflows.

### Universal Scope
MediaDock integrates with any media application exposing the Windows GSMTC API:
- **Spotify** (primary visual design target)
- **Web Browsers** (Google Chrome, Microsoft Edge, Firefox, Brave — YouTube, SoundCloud, web audio)
- **VLC Media Player**
- **Apple Music**
- Other GSMTC-compliant desktop and web media players

---

## 2. Product Vision & Visual Design Language

- **Visual Identity & Hex Customization**: Obsidian Black (`#000000`) default shell and border, dark charcoal (`#141414` – `#222222`) secondary surfaces, subtle dark gray (`#2A2A2A`) borders, white (`#FFFFFF`) primary text, and muted gray (`#8A8A8A`) secondary text. Users can customize the Dynamic Island **Background** and **Border** colors directly using 6-digit hex color codes (`#RRGGBB`) in Settings -> Appearance (with activity status colors removed).
- **Silent Background Operation**: Starts with Windows (or on demand) cleanly in the background via `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, automatically reconciling startup entries and listening for media sessions without requiring user intervention.

---

## 3. Top-Center Notch & Expanded Oval Architecture

MediaDock presents a hybrid top-center overlay: a **flush top-bezel Notch** (`y = 0` with `8px` concave flared ears) when collapsed, morphing cleanly into a floating **Oval Expanded Card** (`y = 12` with `32px` rounded corners) on hover or click.

```
                    ┌──────────────┐
                    │    HIDDEN    │  (No Active Media / Disabled in Settings)
                    └──────┬───────┘
                           │
                     Media detected
                           │
                           ▼
              ┌──────────────────────────────┐  (Flush bezel notch y = 0, 8px flared ears)
              │       COLLAPSED NOTCH        │  (220x34 px, 14px bottom radius)
              │ [Art] Title       ▌▌▌ 12:45  │  (Album thumb, pulse, 12h clock)
              └──────────────┬───────────────┘
                             │
                   Hover / Click Trigger
                             │
                             ▼
              ╭──────────────────────────────╮  (Floating at y = 12, 32px oval corners)
              │       EXPANDED OVAL          │  (Frosted Glass Card 410x178 px / 410x216 w/ lyrics)
              │  [92px Art] Meta / ⚪ Play   │  (Ambient radial cover glow + Pin/Settings dock)
              ╰──────────────┬───────────────╯
                             │
                   Mouse leaves (unless Pinned)
                             │
                    Collapse Delay (ms)
                             │
                             ▼
              ┌──────────────────────────────┐
              │       COLLAPSED NOTCH        │
              └──────────────────────────────┘
```

- **Hybrid Notch-to-Oval Morphing**: Flush top-bezel collapsed notch (`220x34`, `14px` bottom radius, `8px` top flared ears at `y = 0`) morphing cleanly via 180ms `OutCubic` animation into the `32px`-radius floating oval expanded card (`410x178` at `y = 12`, expanding cleanly to `410x216` when synchronized lyrics display) around a constant center X coordinate with zero position drift.
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

### 4.4 Spacious Frosted Gaussian-Blur Preferences UI & Persistence
- **Modern Gaussian Blur Card Dialog**: `820x600` px resizable frosted glass window (`780x560` minimum, Windows 11 DWM Acrylic Gaussian Blur with Windows 10 `SetWindowCompositionAttribute` fallback and translucent glass cards) with a `185px` left navigation sidebar and 6 scrollable, card-grouped stacked pages:
  1. **Preferences**: Grouped into Startup & System Tray, Window & Display, and Media Experience cards (Start with Windows, Start Minimized, Close to Tray, Always on Top, Enable Dynamic Island, Fullscreen Auto-Hide, Target Display Monitor selector, Live Synchronized Lyrics).
  2. **Global Shortcuts**: Interactive shortcut recorders for Show/Hide and Play/Pause plus shortcut guidelines.
  3. **Dynamic Island**: Expansion Trigger (*Hover to Expand* vs *Click to Expand*), Hover Intent Delay (`0–1000 ms`), and Collapse Delay via `CollapseDelaySpinBox` (`500–30000 ms`).
  4. **Appearance**: Custom hex color code (`#RRGGBB`) inputs with live swatches, Reset Default (`#000000`), and live notch preview for Background and Border colors.
  5. **Audio**: Equalizer APO status, Visualizer Spectrum Mode (*True FFT Frequency Spectrum* vs *Time-Domain RMS Energy*), Audio Boost (Preamp), tone controls (bass, clarity, treble, noise gate), and 5-band graphic equalizer with presets.
  6. **About**: Version badge, feature overview, clickable GitHub repository & issue links (`https://github.com/krishnagarg-2004/Mediadock`), and runtime/shortcut quick reference.
- **`SettingsManager`**: Backed by Qt `QSettings` store with explicit synchronization on save and system tray exit, plus startup `AutostartManager.reconcile()` verification.
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
MediaDock includes a comprehensive unit and integration test suite (305 tests covering core models, state machine, notch/oval UI chassis, audio analysis, hotkeys, Equalizer APO, lyrics, hex appearance customization, Gaussian-blur Settings UI, startup reconciliation, and widget lifecycle):
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
- **DeskNotch UI & Visibility Stability Milestone (COMPLETE)**: Transformed MediaDock's UI to match DeskNotch's obsidian glass aesthetic (`220x34` slim bar $\leftrightarrow$ `380x174` expanded notch with `8px`/`10px` top concave flared bezel ears, `14px`/`26px` bottom corner radii, left-centered radial cover glow, frosted media tile with `92x92` rounded `12px` artwork, uppercase player badge + 3-bar pulse + 12h clock, signature solid white circular Play/Pause disc with black glyph, and integrated Pin/Lock + Settings dock buttons), fixed Win32 DPI-aware fullscreen detection (`IsZoomed` / `WS_CAPTION` exclusion + `GetMonitorInfoW`), added `HWND_TOPMOST` Z-order promotion, and isolated test settings (**295 / 295 tests passing**).
- **Startup Reliability, Frosted Gaussian-Blur Settings UI & Hex Appearance Milestone (COMPLETE)**: Fixed Windows startup registration (`AutostartManager.reconcile`, `src/main.py` root `sys.path`/CWD normalization, delayed tray visibility retries for Explorer boot timing, and QSettings/winreg isolation across tests), overhauled `SettingsDialog` into a resizable frosted Gaussian-blur glass workspace (`820x600`, `780x560` minimum, Win11 DWM Acrylic backdrop + Win10 fallback, translucent glass cards), added hex-code (`#RRGGBB`) customization for notch Background & Border with live preview (status colors removed), removed collapsed status dot, placed full-width synchronized lyrics cleanly outside `#MediaTile` so transport buttons remain aligned inside the card, restored flush top-bezel collapsed notch (`y = 0`, `14px` bottom radius, `8px` ears) while preserving the floating oval expanded card (`32px` radius at `y = 12`), and enriched About with clickable GitHub repository links (**305 / 305 tests passing**).
- **Repository Hygiene & Dead-File Cleanup Milestone (COMPLETE)**: Removed unused tracked and workspace files (`MEDIA_DOCK_DEVELOPMENT_HANDOFF.txt` obsolete Phase 9.2 snapshot, empty `0`-byte `LICENSE.txt`, unreferenced `assets/icons/repeat_one.svg` icon, duplicate empty `venv/`, and legacy `scratch/` diagnostic scripts) so `unittest`, bare `pytest`, and PyInstaller builds stay clean (**305 / 305 tests passing**).

### Implemented Codebase vs Target Specification Matrix

| Feature / Component | Current Implementation Codebase | Target V1 Specification Status |
| :--- | :--- | :--- |
| **Application Launch Stability** | Verified (`python -m src.main` and `dist/MediaDock.exe` launch with 0 errors) | Complete |
| **Hybrid Notch & Oval Chassis** | Implemented (Flush `y = 0` collapsed notch `220x34` with `8px` ears & `14px` bottom radius; floating `y = 12` oval expanded card `410x178` / `410x216` with `32px` corners) | Complete |
| **DeskNotch Media Tile & Controls**| Implemented (`#MediaTile` card with solid white `#FFFFFF` Play/Pause disc, rounded `92x92` art, Pin/Lock & Settings dock, and full-width bottom lyrics strip) | Complete |
| **Dynamic Album Art Glow** | Implemented (Ambient radial cover glow centered behind artwork, tinted visualizer and sliders) | Complete |
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
| **Notch Metadata Alignment** | Fixed & Verified (Metadata content group horizontally CENTER and vertically MIDDLE in 220x34 notch) | Complete |
| **Symmetrical Expand Direction** | Fixed & Verified (Expansion originates from centered notch, center X = 960 strictly constant) | Complete |
| **Live Media Source Icons** | Implemented (Spotify desktop/Store, VLC, YouTube metadata validation, `default_media.svg` fallback) | Complete |
| **WASAPI Loopback Capture** | Implemented (`WASAPILoopbackCapture` native COM loopback capture, zero micro-dependency) | Complete |
| **Equalizer APO Integration** | Implemented (`EqualizerAPOManager` detection, config generation, `mediadock_eq.txt` sync) | Complete |
| **Audio Boost & Tone Controls** | Implemented (Preamp boost to +12 dB, Bass low-shelf, Clarity peaking, Treble air, Noise Gate) | Complete |
| **5-Band Graphic Equalizer** | Implemented (60Hz, 250Hz, 1kHz, 4kHz, 16kHz sliders, 6 presets, Flat reset) | Complete |
| **Global Win32 Hotkey Dispatch** | Implemented (HWND message target, Shiboken VoidPtr fix, `Ctrl+Alt+S` / `Ctrl+Alt+Space`) | Complete |
| **Global Shortcut Recorder UI** | Implemented (`ShortcutRecorderWidget` interactive keycap pills with `+` labels, 2/3-key validation, rollback) | Complete |
| **Frosted Gaussian-Blur Settings UI** | Implemented (`820x600` resizable Win11 DWM Acrylic / Win10 Composition frosted glass window, `185px` sidebar, 6 scrollable card-grouped pages, GitHub-linked About tab) | Complete |
| **Custom Hex Appearance System** | Implemented (User-configurable `#RRGGBB` hex Background & Border with live preview & Reset Default) | Complete |
| **Windows Startup Reconciliation** | Implemented (`AutostartManager.reconcile()` HKCU registry path normalization, root `sys.path`/CWD guard, delayed Explorer tray sync) | Complete |

### Verification & Release Summary
- **Source Launch Status**: `python -m src.main` -> **SUCCESSFUL**
- **Automated Test Suite**: **305 / 305 tests passing** cleanly (`.venv\Scripts\python.exe -m unittest discover -s tests`).
- **Whitespace & Formatting**: `git diff --check` clean (0 errors).
- **Standalone Executable Build**: `MediaDock.spec` PyInstaller build completed cleanly (`dist/MediaDock.exe`).

---

## 7. Multi-Phase Roadmap

- **V1 & DeskNotch Baseline (Current - Complete)**:
  - Hybrid top-center notch (`220x34` flush bar with `8px` concave bezel ears & `14px` bottom corners at `y = 0` $\leftrightarrow$ `410x178` / `410x216` floating oval glass card with `32px` corners at `y = 12`).
  - Ambient album-art radial glow, mirrored waveform visualizer, interactive scrub slider with timestamp tooltip, Pin/Lock & Settings dock buttons.
  - Symmetrical 180ms `OutCubic` morphing with zero position drift and HWND_TOPMOST Z-order promotion.
  - GSMTC universal media detection, multi-session switcher pill, shuffle & repeat toggles, and async LRCLIB synchronized lyrics.
  - CoreAudio master/app volume control, WASAPI loopback capture, pure-Python Radix-2 FFT frequency spectrum & RMS energy analyzer.
  - Equalizer APO integration: Audio boost (+12 dB preamp), quick tone controls, and 5-band graphic EQ with dynamic visualizer coupling.
  - DPI-safe Win32 fullscreen game/video auto-hide, multi-monitor anchoring, Win32 global hotkeys with interactive 2/3-key recorder UI.
  - Frosted Gaussian-blur Preferences dialog (`Appearance` hex customization, GitHub-linked `About` page), single-instance IPC guard, verified Windows startup reconciliation, **305/305 test coverage**, and standalone PyInstaller build.

- **V2 (Future Productivity & Desk Integration)**:
  - Focus/Pomodoro countdown timer & micro-task strip inside expanded notch.
  - Drag-and-drop transient file shelf in expanded view.
  - Visualizer attack/decay smoothing sliders in Audio Settings.
  - Automatic follow-active-cursor monitor mode.

---

## 8. Documentation Index

- [**Technical Architecture Manual**](docs/architecture.md) — Comprehensive technical reference, component diagrams, signal flows, and OS integration details.
- [**User & Operations Guide**](docs/user_guide.md) — User setup, shortcuts, and operation details.
