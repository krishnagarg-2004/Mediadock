# MediaDock

**MediaDock** is a native Windows 10 / 11 desktop media overlay inspired by Dynamic Island / DeskNotch. Built with **Python 3.14**, **PySide6**, and **WinRT (GSMTC)**, it detects active media across apps like **Spotify**, **YouTube (Chrome / Edge / Brave / Firefox)**, **VLC**, and **Apple Music**, showing a sleek top-center notch that expands into an interactive frosted media card.

---

## Key Features

- **Universal Windows Media Control**: Works automatically with any player that supports Windows Global System Media Transport Controls (GSMTC), with quick switching when multiple media apps are open.
- **Hybrid Top-Center Design**:
  - **Collapsed Notch (`220 × 34` px)**: Sits flush against the top edge of your screen (`y = 0`) with curved bezel ears, rounded mini artwork or app icon, track title, 3-bar audio pulse, and 12-hour clock.
  - **Expanded Oval Card (`410 × 178` px)**: Smoothly drops into a floating rounded card (`y = 12`) with album artwork, ambient color glow, playback controls (Previous, Play/Pause, Next, Shuffle, Repeat), interactive progress scrub bar, Pin lock, and live **Synchronized Lyrics** (`410 × 216` px).
  - **Synchronized Lyrics Drawer / Modal**: Click the single-line lyrics preview to open a floating translucent frosted-glass drawer with full multi-line lyrics, active line auto-scrolling, dynamic album-art accent highlighting, and click-to-seek song playback.
- **Real-Time Audio Visualizer**: Captures live desktop audio output using Windows WASAPI loopback and renders a mirrored waveform in either **True FFT Frequency Spectrum** or **RMS Energy** mode.
- **System Equalizer Bridge (via Equalizer APO)**: Includes a `+12 dB` preamp boost, bass/clarity/treble tone sliders, noise gate, and 5-band graphic EQ presets *(see [How Audio Connects to Your PC](#how-audio-settings-connect-to-your-pc))*.
- **Rich Appearance Customization**: Choose **Solid Hex Colors (`#RRGGBB`)**, **8 Gradient Presets or Custom 2/3-Stop Gradients** across **7 Styles**, or **Custom Banner Images** set separately for the **Collapsed Notch** and **Expanded Card** with live previews.
- **Frosted Gaussian-Blur Settings UI**: Native Windows 11 DWM Acrylic blur dialog (with Windows 10 fallback) organized into 6 clean scrollable sections, featuring an integrated **GitHub Update Checker**.
- **Desktop & Display Integration**: System tray controls, global OS hotkeys (`Ctrl+Alt+S` and `Ctrl+Alt+Space`), fullscreen game/video auto-hide, dynamic multi-monitor hotplug & resolution re-anchoring, single-instance protection, and Windows startup integration.
- **Automated CI/CD & Installer**: Full GitHub Actions test suite and automated release publisher, with Inno Setup Windows installer (`MediaDock-Setup.exe`) and standalone PyInstaller executable (`MediaDock.exe`).

---

## How the Overlay Works

```text
  No media active ──► HIDDEN (runs quietly in System Tray)
         │
   Media starts
         ▼
  ┌──────────────────────────┐
  │ 🎵 Song Title    ▌▌▌ 9:41 │  ◄── COLLAPSED NOTCH (flush at top edge y = 0)
  └────────────┬─────────────┘
         Hover or Click
               ▼
  ╭──────────────────────────╮
  │  ┌────┐  SPOTIFY  ▶ / ⏸  │
  │  │Art │  Song & Artist   │  ◄── EXPANDED OVAL CARD (floating at y = 12)
  │  └────┘  ⏮ ⚪ ⏭  🔀 🔁    │
  │   ♪ Synced Lyrics Strip   │
  │  01:12 ━━●━━━━━━━ 03:40  │
  ╰──────────────────────────╯
```

- **Auto-Hide & Auto-Collapse**: Stays invisible when nothing is playing, expands on hover or click, and collapses after a configurable delay (`500 ms` – `30,000 ms`) once the pointer moves away (unless pinned with the lock icon).

---

## How Audio Settings Connect to Your PC

MediaDock connects its audio controls and settings to Windows across three layers:

| Audio Feature | Connected to Your PC? | How It Works on Any Computer |
| :--- | :--- | :--- |
| **Card Master Volume Slider & Mute (`CoreAudio`)** | **Yes (Connected Out-of-the-Box)** | Directly reads and controls your Windows default playback endpoint (`IAudioEndpointVolume`), syncing automatically with external Windows volume/mute changes and device switches (headphones, speakers, Bluetooth). |
| **Playback, Shuffle, Repeat & Scrub Bar (`GSMTC`)** | **Yes (Connected Out-of-the-Box)** | Controls system media sessions directly via WinRT GSMTC (`winrt-Windows.Media` + `winrt-Windows.Media.Control`) with active Shuffle & Repeat state highlighting. |
| **Live Visualizer (`WASAPI Loopback`)** | **Yes (Real-Time Audio Capture)** | Listens directly to your default Windows audio playback so the waveform bars bounce in real time to music, videos, or games. |
| **System Equalizer & `+12 dB` Audio Booster** | **Permission-Prompted Live Setup** | Always updates MediaDock's **visualizer bars** immediately (**Noise Gate** filters the visualizer). To adjust **real speaker/headphone sound** (Preamp `+12 dB`, Bass, Clarity, Treble, 5-Band EQ), MediaDock asks permission on first launch (or via **Settings → Audio & Equalizer**) to download/install [**Equalizer APO**](https://equalizerapo.com/download.html), grant Windows UAC write access to `mediadock_eq.txt`, and open the Audio Device Selector so you can attach it to your playback device. |

> **Tip**: Check **Settings → Audio & Equalizer** anytime to view your live CoreAudio volume connection and Equalizer APO status, click **Allow & Connect Audio...** / **Grant Permission & Connect**, or open **Audio Devices...** to pick which speakers/headphones are boosted.

---

## Settings & Customization Overview

Open **Preferences** from the gear icon (`⚙`) on the expanded card or by right-clicking the System Tray icon:

1. **Preferences**: *Start with Windows*, *Start Minimized*, *Close to Tray*, *Always on Top*, *Enable Dynamic Island*, *Auto-Hide in Fullscreen Games & Apps*, *Target Display Monitor*, and *Live Synchronized Lyrics*.
2. **Global Shortcuts**: Record custom 2-key or 3-key Windows shortcuts (defaults: `Ctrl+Alt+S` to Show/Hide, `Ctrl+Alt+Space` for Play/Pause).
3. **Dynamic Island**: Pick *Hover* or *Click* to expand, *Hover Intent Delay* (`0–1000 ms`), and *Collapse Delay* (`500–30000 ms`).
4. **Appearance**:
   - **Background Style**: *Solid Color* (`#RRGGBB` hex), *Gradient*, or *Custom Banner Image*.
   - **Border Color**: Custom `#RRGGBB` outline for both collapsed and expanded shapes.
   - **Gradient Options**: 8 presets (*Aurora*, *Cyber Mint*, *Midnight Neon*, *Sunset Ember*, *Royal Velvet*, *Deep Ocean*, *Rose Quartz*, *Obsidian Steel*) or *Custom* 2/3-stop hex colors, across **7 styles** (*Diagonal*, *Horizontal*, *Vertical*, *Reverse Diagonal*, *Radial*, *Conic Sweep*, *Dual-Tone Mesh*).
   - **Custom Image Banners**: Pick separate `PNG`/`JPG`/`WEBP`/`BMP` images for the **Expanded Card Banner** and **Collapsed Notch Banner** (or copy expanded to collapsed with one click), set *Center/Top/Bottom* crop focus, adjust **Banner Overlay Dim** (`0–85%`), and preview both versions live.
5. **Audio & Equalizer**: Live CoreAudio Master Volume & Equalizer APO connection status, **Allow & Connect Audio...** permission installer/UAC setup, **Audio Devices...** selector, *Apply Audio Now*, *True FFT* vs *RMS* visualizer mode, `+12 dB` Preamp, Bass/Clarity/Treble sliders, Noise Gate, and 5-band Graphic EQ (`60 Hz` – `16 kHz`) with presets.
6. **About**: App info, shortcut summary, one-click **Check for Updates** button querying GitHub Releases, clickable repository links, and support contact (`krishna.garg.support@gmail.com` for suggestions, feedback, questions, or issues).

---

## Quick Start (Run From Source)

### Prerequisites
- **Windows 10 or Windows 11** (64-bit)
- **Python 3.10+** (Python 3.14 recommended)

### Setup & Launch
```cmd
git clone https://github.com/krishnagarg-2004/Mediadock.git
cd Mediadock

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python -m src.main
```

### Run Tests & Build `.exe`
- **Run full automated test suite (327 tests)**:
  ```cmd
  .venv\Scripts\python.exe -m unittest discover -s tests
  ```
- **Run with pytest**:
  ```cmd
  .venv\Scripts\python.exe -m pytest -q
  ```
- **Check formatting / whitespace**:
  ```cmd
  git diff --check
  ```
- **Build standalone `dist/MediaDock.exe` & Windows Installer**:
  ```cmd
  .venv\Scripts\python.exe scripts/build.py
  ```

---

## Project Structure

```text
Mediadock/
├── .github/workflows/   # Automated CI/CD test and release pipeline (release.yml)
├── assets/icons/        # SVG icons for transport controls, volume, pin, settings & players
├── docs/                # Detailed technical architecture & user operation guides
├── installer/           # Inno Setup 6 installer specification (installer.iss)
├── scripts/build.py     # PyInstaller packaging & Inno Setup build pipeline -> dist/
├── src/
│   ├── core/            # MediaCore coordinator, data models, QSettings manager, IPC & fullscreen guard
│   ├── media/           # WinRT GSMTC, WASAPI loopback capture, FFT/RMS analyzer, EQ APO, CoreAudio, Lyrics
│   ├── ui/              # Hybrid notch/oval MainWindow, lyrics drawer, SettingsDialog, SystemTray, Hotkeys
│   ├── utils/           # Windows HKCU Run startup registry helper
│   └── main.py          # App entrypoint, single-instance guard & tray bootstrap
├── tests/               # 327 unit & integration tests across 35 test modules
├── MediaDock.spec       # PyInstaller executable specification
└── requirements.txt     # Python runtime & build dependencies
```

---

## Further Documentation & Milestones

- [**Technical Architecture Manual**](docs/architecture.md) — Internal component diagram, data models, OS APIs, and startup flow.
- [**User & Operations Guide**](docs/user_guide.md) — Step-by-step usage, shortcuts, and troubleshooting.

---

## Contact & Support

For suggestions, feedback, questions, or to report an issue:

📧 **[krishna.garg.support@gmail.com](mailto:krishna.garg.support@gmail.com)**

You can also open a [GitHub Issue](https://github.com/krishnagarg-2004/Mediadock/issues) directly on the repository.

---

<details>
<summary><strong>Development Milestone History (Click to expand)</strong></summary>

- **Foundation through V1.5**: Core WinRT GSMTC session detection, multi-session switcher, WASAPI loopback + Radix-2 FFT/RMS visualizer, Equalizer APO bridge, interactive scrubbing, album-art ambient glow, shuffle/repeat toggles, fullscreen game auto-hide, multi-monitor anchoring, Win32 global hotkeys with interactive shortcut recorder, and standalone PyInstaller packaging (**286 tests**).
- **DeskNotch Chassis & Visibility Stability**: Hybrid flush notch / frosted glass card silhouette, Win32 DPI-safe fullscreen checks, `HWND_TOPMOST` Z-order handling, and test registry isolation (**295 tests**).
- **Startup Fix, Frosted Gaussian-Blur Settings & Hex Appearance**: Fixed Windows startup path reconciliation and Explorer boot tray retries, redesigned `SettingsDialog` (`820×600`) with Windows 11 DWM Acrylic blur + translucent glass cards, added `#RRGGBB` hex background/border inputs, moved lyrics below `#MediaTile`, and restored hybrid flush collapsed notch (`y = 0`) + floating oval expanded card (`y = 12`) (**305 tests**).
- **Repository Cleanup**: Removed obsolete handoff notes, empty 0-byte license placeholder, unused SVG icon, legacy `scratch/` scripts, and duplicate `venv/` folder.
- **Custom Gradients & Expanded/Collapsed Banner Images**: Added shared `NotchAppearance` / `paint_notch_surface` renderer, 8 gradient presets + Custom 2/3-stop hex stops in 7 gradient styles, independent Expanded & Collapsed banner image pickers with crop focus, overlay dim slider, `QPixmap` mtime caching, and dual live previews (**309 tests**).
- **Windows Audio & Control Connection Upgrade**: Fixed CoreAudio `IAudioEndpointVolume` COM GUID with live external volume/device sync for the card master volume slider & mute button, added `winrt-Windows.Media` support for GSMTC Shuffle/Repeat active button states, cleaned WASAPI COM allocations, and added a one-time permission flow (`Allow & Connect Audio...`) to install/grant UAC permissions for Equalizer APO + `+12 dB` Audio Booster on any Windows PC (**315 tests passing**).
- **Lyrics, UX Polish & Bug Fixes**: 3-tier synchronized lyrics fetching with metadata sanitization and stale-fetch race handling; fixed shuffle/repeat active-state button highlight (icon color only, no background square); Windows volume OSD overlay restored (zero-GUID event context in CoreAudio calls); mouse-wheel no longer accidentally changes Settings controls — values only change via click; Reset button in Appearance simplified; support contact email added to About page (**322 tests passing**).
- **V1.0.0 Release Architecture & Enhancements**: Interactive multi-line synchronized lyrics drawer with line auto-scrolling, dynamic album accent highlighting, and click-to-seek playback; dynamic multi-monitor display hotplug and resolution re-anchoring; GitHub Releases update checker in Settings About tab; Inno Setup Windows installer script (`MediaDock-Setup.exe`); and GitHub Actions CI/CD release workflow for automated testing and release publishing (**327 tests passing**).

</details>
