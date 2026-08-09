# Project Status

Current Milestone:
Milestone 7 — Media Source & Control Expansion (Completed)

Current Task:
MediaDock v1.0 Production Release Ready

Completed:
- Project Bible created
- Repository initialized
- Milestone 1 Foundation completed (`FramelessWindow`, `MainWindow`, PySide6 entry point)
- Milestone 2 Windows Media Detection completed (`BaseMediaProvider`, `GSMTCProvider`, `MediaCore`, PyWinRT session listening, metadata extraction)
- Milestone 3 Connected UI & Advanced Controls completed (Transport control abstraction, GSMTC async dispatches, MediaCore routing, interactive controls, seeking state machine)
- Milestone 4 Visual Polish & Dynamic Styling completed (Catppuccin Mocha tokens, QSS styling, `ElidedLabel`, status badges, opacity animations, album-art color extraction)
- Milestone 5 System Tray & Settings completed (`SettingsManager`, `SystemTrayIcon`, `SettingsDialog`, lifecycle integration)
- Milestone 6 Advanced Features, OS Integration & Packaging completed:
  - Step 1: Windows Autostart Integration (`AutostartManager`, `winreg` HKCU registry key creation/deletion)
  - Step 2: Global Keyboard Shortcuts (`GlobalHotkeyManager`, Win32 `WM_HOTKEY` registration)
  - Step 3: Standalone PyInstaller Packaging Spec & Build System (`MediaDock.spec`, `scripts/build.py`)
  - Step 4: Technical Architecture Manual (`docs/architecture.md`) & User Guide (`docs/user_guide.md`)
  - Step 5: Final Release Verification
- Milestone 7 Media Source & Control Expansion completed:
  - Step 1: GSMTC Multi-Session Architecture & App Selection (`MediaSessionInfo`, session enumeration, fallback state, system tray source selector menu)
  - Step 2: Master Volume & Mute Control (`VolumeState`, `BaseVolumeProvider`, `WindowsVolumeProvider`, CoreAudio `IAudioEndpointVolume` COM integration, vector speaker icons, graceful unsupported fallback)
  - Step 3: Configurable Global Hotkeys (`parse_key_sequence`, dynamic modifier/virtual key string parsing, collision detection, safe rollback state machine, `SettingsDialog` fields)
  - Step 4: Desktop UX — Compact Mode & Edge Snapping (Mini 240x48 view mode, title elision, multi-monitor 15px edge snapping via `QScreen.availableGeometry()`, right-click context menu)
  - Step 5: End-to-End Release Verification & Documentation

Next:
- MediaDock v1.0 Production Release Finalized

Known Issues:
None

Verification & Release Summary:
- **1. Automated Regression Suite**: 141 / 141 tests passing (`0.835s`).
- **2. Executable / Process / Runtime Verification**: Standalone executable `dist/MediaDock.exe` (45.80 MB / 48,026,163 bytes, single windowed GUI executable, PyWinRT & PySide6 embedded). Verified background process execution (`--minimized`), memory allocation, and clean process termination.
- **3. Physical / Manual UI Verification**: Requires manual physical desktop interaction on a host Windows display for real-time mouse dragging, physical hotkey pressing, visual Catppuccin rendering, and system tray menu interaction.
