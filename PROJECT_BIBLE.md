# MediaDock Project Bible

This document serves as the authoritative source of truth for **MediaDock**. It defines the product identity, product direction, system architecture, technology stack, application lifecycle, state model, V1 feature specification, fixed visual identity, and multi-phase roadmap.

---

## 1. Project Identity

- **Project Name**: MediaDock
- **Executable Name**: `MediaDock.exe`
- **Platform**: Windows Desktop (Windows 10 / 11)
- **Target Audience**: Windows desktop users desiring non-intrusive, universal media controls.

**MediaDock** is a native Windows desktop media application presented as a top-center **"Dynamic Island"** overlay.

### Core Identity Guidelines:
1. **Name Stability**: "MediaDock" is the official project name. Do not rename the project, executable, package, repository, or application icon.
2. **Universal Scope**: MediaDock is designed as a universal Windows media platform. It integrates with any media application exposing the Windows Global System Media Transport Controls (GSMTC) API, including:
   - Spotify (primary visual design target)
   - Google Chrome / Microsoft Edge (YouTube, SoundCloud, web audio)
   - VLC Media Player
   - Apple Music
   - Other GSMTC-compliant desktop or web media players
3. **Architecture Reusability**: The core media engine ([`MediaCore`](file:///c:/Users/krish/Projects/SpotifyProject_OOC1/src/core/media_core.py)) is kept independent of the visual presentation layer so it can be reused in future systems or alternative frontends.
4. **Unique Product Identity**: MediaDock draws inspiration from Apple's Dynamic Island interaction model, Nothing OS visual minimalism, and NotchNook-style top-center desktop utility concepts, while maintaining its own distinct visual identity on Windows.

---

## 2. Product Definition

MediaDock runs as a lightweight, background desktop utility that monitors system-wide audio and media playback in real-time.

MediaDock presents a top-center **Windows Dynamic Island**. It stays silently hidden when no media is active and automatically presents a sleek top-center collapsed capsule when media playback is detected. When hovered, the capsule seamlessly expands into an interactive media card allowing users to view metadata (track title, artist, album art) and issue media commands (play/pause, skip, volume adjustment, mute) without disrupting their desktop workflow.

---

## 3. Product Vision & Visual Design Language

- **Fixed System Visual Identity**: Pure Black (`#000000`) background & border, dark charcoal (`#141414` - `#222222`) secondary surfaces, subtle dark gray (`#2A2A2A`) panel borders, white (`#FFFFFF`) primary text, muted gray (`#8A8A8A`) secondary text, and system-defined status indicators:
  - **ACTIVE / PLAYING**: Spring Green (`#00FF7F`)
  - **INACTIVE / PAUSED / STOPPED / CLOSED**: Crimson Red (`#C1121C`)
- **Non-Customizable Product Colors**: The Dynamic Island background (`#000000`), border (`#000000`), and status dot colors (`#00FF7F` / `#C1121C`) are fixed by the product visual identity and cannot be customized by user settings.
- **Silent Background Operation**: Starts with Windows (or on demand) silently in the background, listening for media sessions without requiring user intervention.
- **Symmetrical Dynamic Island Morphing**: Expands and contracts outward from a constant center X coordinate (`180x40` capsule ↔ `360x160` expanded card) with `OutCubic` 180ms easing and zero right-side clipping or pop-out jumps.
- **Landscape Preferences Architecture**: Modern landscape settings window (`680x440` px) with persistent left navigation sidebar (`QListWidget`) and right content area (`QStackedWidget`) featuring 6 pages: Preferences, Global Shortcuts, Dynamic Island, Appearance, Audio, and About.

---

## 4. Dynamic Island Architecture & State Model

MediaDock presents a top-center, non-draggable overlay anchored to the primary display.

```
                    ┌──────────────┐
                    │    HIDDEN    │  (No Active Media / Disabled in Settings)
                    └──────┬───────┘
                           │
                     Media detected
                           │
                           ▼
                    ┌──────────────┐
                    │  COLLAPSED   │  (Top-Center Minimal Capsule 180x40 px)
                    │   CAPSULE    │  [Source Icon] Title — Artist  ●
                    └──────┬───────┘
                           │
                       Mouse hover
                           │
                           ▼
                    ┌──────────────┐
                    │   EXPANDED   │  (Interactive Media Card 360x160 px)
                    │  MEDIA CARD  │  [Art] Title / Artist / Controls / Volume
                    └──────┬───────┘
                           │
                    Mouse leaves
                           │
                   Collapse Delay (ms)
                           │
                           ▼
                    ┌──────────────┐
                    │  COLLAPSED   │
                    └──────────────┘
```

---

## 5. Win32 Global Hotkey Dispatch System

MediaDock registers OS-wide global hotkeys with Windows User32 API using `RegisterHotKey(target_hwnd, id, modifiers, vk)`:
- **Show / Hide MediaDock**: `Ctrl+Alt+S` (strictly 2 or 3 keys required)
- **Toggle Play / Pause**: `Ctrl+Alt+Space` (strictly 2 or 3 keys required)
- **Native Event Filter**: `HotkeyNativeEventFilter` intercepts `WM_HOTKEY` (0x0312) messages dispatched to `target_hwnd` (`window.winId()`) and checks `message is not None` to safely handle PySide6 Shiboken `VoidPtr` objects.

---

## 6. Implementation & Launch Regression Resolution

- **Launch Regression Resolution**: Resolved a variable scoping bug in `src/main.py` where line 99 referenced `main_window.winId()` instead of `window.winId()`. Corrected reference to `window.winId()`.
- **Bug Fix & Polish Milestone (V1 Final Core Issues Resolved)**:
  - **Issue 1 — Preferences Persistence Lifecycle on System Tray Exit**: Resolved issue where re-opening an existing `SettingsDialog` instance retained stale UI control states and `sync()` was not invoked prior to tray exit termination. Fixed by adding `showEvent()` refresh in `SettingsDialog`, invoking `load_settings()` on every dialog open in `main.py`, calling `SettingsManager.sync()` explicitly in `save_settings()`, and syncing `SettingsManager` in `quit_application()`. QSettings preserved as single source of truth.
  - **Issue 2 — Collapsed Metadata Vertical Alignment**: Resolved metadata top-alignment shift post-collapse animation. Root cause identified in `_capsule_widget` size constraints remaining unconstrained after animation finished, causing `_capsule_widget` to shrink to 26px height. Fixed by restoring `_capsule_widget.setFixedSize(180, 40)` in `_on_geom_anim_finished()`, guaranteeing `capsule.center().y() == 20.0` and `metadata_group.center().y() == 20.0` (MIDDLE and CENTER alignment preserved before and after hover cycles).
  - **Issue 3 — Collapsed → Expanded Animation Direction**: Fixed visual asymmetric right-side entry during `COLLAPSED → EXPANDED` expansion by locking `_expanded_widget.setFixedSize(360, 160)` upon animation completion while scaling layout bounds symmetrically around center X = 960 throughout expansion, preserving `EXPANDED → COLLAPSED` collapse animation behavior intact.
- **Source Launch Verification**: Source application (`python -m src.main`) verified launching and running with zero exceptions.
- **Packaged Launch Verification**: Packaged executable (`dist/MediaDock.exe`) verified launching, saving preferences through System Tray exit/relaunch, and zero-drift morphing.
- **Automated Test Suite**: **258 / 258 tests passing** cleanly (`10.61s`).
- **Git Diff Formatting**: 0 errors on `git diff --check`.
- **Packaged Executable Build**: `dist/MediaDock.exe` built and verified cleanly.
- **Known Issues**: None.
