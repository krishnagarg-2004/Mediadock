"""Dynamic Island presentation components: ReactiveVisualizerWidget and CollapsedCapsuleWidget."""

import math
from typing import Optional, Union
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QFont
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from src.core.models import PlaybackStatus
from src.ui.components import ElidedLabel
from src.ui.theme import (
    COLOR_BG_ISLAND,
    COLOR_STATUS_ACTIVE,
    COLOR_STATUS_INACTIVE,
    COLOR_ACCENT_BLUE,
    get_svg_pixmap,
)


class ReactiveVisualizerWidget(QWidget):
    """Reusable presentation-only reactive visualizer.

    Renders real-time waveform bars reacting strictly to system audio analysis data.
    Does NOT use artificial/synthetic animation timers when audio is silent or unavailable.
    """

    def __init__(
        self,
        bar_count: int = 5,
        bar_color: QColor = COLOR_ACCENT_BLUE,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._bar_count = max(3, bar_count)
        self._bar_color = bar_color
        self._is_playing: bool = False
        self._realtime_bars: Optional[List[float]] = None

        # Fixed height & proportional width container defaults
        self.setMinimumSize(24, 16)

    @property
    def is_animated(self) -> bool:
        """Return True if real-time audio playback is active and bar heights are available."""
        return self._is_playing and self._realtime_bars is not None

    def set_bar_color(self, color: QColor) -> None:
        """Update waveform bar accent color."""
        self._bar_color = color
        self.update()

    def set_bar_heights(self, bar_heights: Sequence[float]) -> None:
        """Update real-time bar heights from AudioAnalyzer (normalized 0.0 to 1.0)."""
        if bar_heights:
            self._realtime_bars = [max(0.0, min(1.0, float(h))) for h in bar_heights]
            if len(self._realtime_bars) != self._bar_count:
                self._bar_count = len(self._realtime_bars)
            self.update()

    def clear_bar_heights(self) -> None:
        """Clear real-time bar heights, returning visualizer to static baseline state."""
        if self._realtime_bars is not None:
            self._realtime_bars = None
            self.update()

    def set_playback_status(self, status: Union[PlaybackStatus, str]) -> None:
        """Update active status based on playback state."""
        status_str = status.value if isinstance(status, PlaybackStatus) else str(status)
        is_playing = (status_str.upper() == "PLAYING")

        if is_playing != self._is_playing:
            self._is_playing = is_playing
            if not self._is_playing:
                self.clear_bar_heights()
            else:
                self.update()

    def paintEvent(self, event) -> None:
        """Paint anti-aliased rounded waveform bars reacting strictly to real-time audio or static baseline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        spacing = 2
        total_spacing = spacing * (self._bar_count - 1)
        bar_width = max(2.0, (w - total_spacing) / self._bar_count)

        for i in range(self._bar_count):
            if self._is_playing and self._realtime_bars and i < len(self._realtime_bars):
                # Real-time audio analyzer bar height
                height_factor = max(0.05, min(1.0, self._realtime_bars[i]))
            else:
                # Subdued static baseline bar height when paused, stopped, silent, or capture unavailable
                height_factor = 0.20

            bar_h = max(3.0, h * height_factor)
            x = i * (bar_width + spacing)
            y = h - bar_h

            rect = QRectF(x, y, bar_width, bar_h)
            path = QPainterPath()
            path.addRoundedRect(rect, bar_width / 2.0, bar_width / 2.0)

            painter.fillPath(path, self._bar_color)

        painter.end()


def classify_media_source(source_name: str, title: str = "", artist: str = "") -> str:
    """Classify media source name and metadata into normalized source keys: 'spotify', 'youtube', 'vlc', or 'default_media'."""
    source_lower = source_name.lower() if source_name else ""
    title_lower = title.lower() if title else ""
    artist_lower = artist.lower() if artist else ""

    # 1. Spotify (matches "spotify", "Spotify.exe", "SpotifyAB.SpotifyMusic_...", etc.)
    if "spotify" in source_lower or "spotify" in artist_lower or "spotify" in title_lower:
        return "spotify"

    # 2. VLC Media Player (matches "vlc", "vlc.exe", "VLC Media Player")
    if "vlc" in source_lower:
        return "vlc"

    # 3. YouTube (matches explicit "youtube" in source_name, or browser session with "youtube" in title/artist)
    if "youtube" in source_lower:
        return "youtube"

    is_browser = any(b in source_lower for b in ("chrome", "edge", "msedge", "firefox", "brave", "opera"))
    if is_browser:
        if "youtube" in title_lower or "youtube" in artist_lower:
            return "youtube"
        return "default_media"

    if "youtube" in title_lower or "youtube" in artist_lower:
        return "youtube"

    # 4. Unknown / Default Fallback
    return "default_media"


class CollapsedNotchWidget(QWidget):
    """Reusable presentation-only top-center Dynamic Island collapsed notch screen (180x40 px target)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(180, 40)
        self._bg_color = COLOR_BG_ISLAND  # #000000 Pure Black
        self._border_color = QColor("#000000")  # Pure Black border
        self._accent_color = COLOR_ACCENT_BLUE
        self._current_source_name: str = ""
        self._current_icon_name: str = "default_media"

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize compact internal horizontal layout centered both horizontally and vertically."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Left Column: Media / App Icon (18x18)
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(18, 18)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_default_icon()

        # Center Column: Elided Track Title Label (Horizontally & Vertically Centered)
        self.title_label = ElidedLabel("MediaDock", self)
        font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #FFFFFF;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Right Column: Status Dot Indicator (8x8)
        self.status_dot = QLabel(self)
        self.status_dot.setFixedSize(8, 8)
        self.set_playback_status(PlaybackStatus.CLOSED)

        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.title_label, 1, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.status_dot, 0, Qt.AlignmentFlag.AlignVCenter)

    def _set_default_icon(self) -> None:
        """Set default media SVG icon pixmap."""
        self._current_icon_name = "default_media"
        pixmap = get_svg_pixmap("default_media", size=18, color=self._accent_color)
        self.icon_label.setPixmap(pixmap)

    def set_source_info(self, source_name: str, title: str, artist: str = "") -> None:
        """Set source-aware app icon and elided track/video label."""
        self._current_source_name = source_name or ""
        icon_name = classify_media_source(source_name, title, artist)
        self._current_icon_name = icon_name

        if icon_name == "spotify":
            icon_color = QColor("#1DB954")
        elif icon_name == "youtube":
            icon_color = QColor("#FF0000")
        elif icon_name == "vlc":
            icon_color = QColor("#FF8800")
        else:
            icon_color = self._accent_color

        pixmap = get_svg_pixmap(icon_name, size=18, color=icon_color)
        self.icon_label.setPixmap(pixmap)

        display_title = title.strip() if title else "MediaDock"
        artist_clean = artist.strip() if artist else ""

        if artist_clean:
            full_text = f"{display_title} — {artist_clean}"
        else:
            full_text = display_title

        self.title_label.setText(full_text)

    def set_track_title(self, title: str) -> None:
        """Update displayed track title or app name in capsule."""
        self.title_label.setText(title if title else "MediaDock")

    def set_app_icon(self, pixmap: Optional[QPixmap]) -> None:
        """Update app icon pixmap or restore default SVG icon."""
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                20,
                20,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.icon_label.setPixmap(scaled)
        else:
            self._set_default_icon()

    def set_playback_status(self, status: Union[PlaybackStatus, str]) -> None:
        """Update status dot color indicator (GREEN = PLAYING, RED = INACTIVE)."""
        status_str = status.value if isinstance(status, PlaybackStatus) else str(status)
        status_upper = status_str.upper()

        if status_upper == "PLAYING":
            color_hex = COLOR_STATUS_ACTIVE.name()  # GREEN #A6E3A1
        else:
            color_hex = COLOR_STATUS_INACTIVE.name()  # RED #F38BA8

        self.status_dot.setStyleSheet(
            f"background-color: {color_hex}; border-radius: 4px;"
        )

    def set_accent_color(self, color: QColor) -> None:
        """Update capsule accent tint color."""
        self._accent_color = color
        self.update()

    def paintEvent(self, event) -> None:
        """Paint clean notch background (flat top edge flush with screen bezel, rounded bottom corners)."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.0, -0.5, -0.5)
        r = 16.0
        path = QPainterPath()
        path.moveTo(rect.left(), rect.top())
        path.lineTo(rect.right(), rect.top())
        path.lineTo(rect.right(), rect.bottom() - r)
        path.quadTo(rect.right(), rect.bottom(), rect.right() - r, rect.bottom())
        path.lineTo(rect.left() + r, rect.bottom())
        path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - r)
        path.closeSubpath()

        painter.fillPath(path, self._bg_color)
        pen = QPen(self._border_color, 1.0)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()


# Backward compatibility alias for existing consumers and tests
CollapsedCapsuleWidget = CollapsedNotchWidget
