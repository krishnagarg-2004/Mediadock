import os
import sys
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from src.core.models import PlaybackStatus

# --- Design Tokens & Centralized Color Architecture ---
COLOR_BG_ISLAND = QColor("#000000")  # Pure Black baseline for capsule & expanded card
COLOR_BORDER_ISLAND = QColor("#000000")  # Pure Black border baseline
COLOR_STATUS_ACTIVE = QColor("#00FF7F")  # System-defined GREEN (#00FF7F) for active playing status
COLOR_STATUS_INACTIVE = QColor("#C1121C")  # System-defined RED (#C1121C) for inactive/paused status

COLOR_BG_BASE = QColor("#000000")
COLOR_BG_MANTLE = QColor("#141414")
COLOR_BG_SURFACE = QColor("#222222")
COLOR_BORDER = QColor("#2A2A2A")

COLOR_TEXT_PRIMARY = QColor("#FFFFFF")
COLOR_TEXT_SECONDARY = QColor("#A0A0A0")
COLOR_TEXT_MUTED = QColor("#8A8A8A")

COLOR_ACCENT_GREEN = QColor("#00FF7F")
COLOR_ACCENT_YELLOW = QColor("#E5C07B")
COLOR_ACCENT_RED = QColor("#C1121C")
COLOR_ACCENT_BLUE = QColor("#00FF7F")

# Icon Assets Path (supports PySide6 / PyInstaller frozen bundle)
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ASSETS_ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")


def get_svg_pixmap(
    name: str,
    size: int = 24,
    color: Optional[QColor] = None,
    fallback_name: str = "default_media",
) -> QPixmap:
    """Load an SVG icon from assets/icons/{name}.svg and render crisp QPixmap with optional tint color."""
    icon_path = os.path.join(ASSETS_ICONS_DIR, f"{name}.svg")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(ASSETS_ICONS_DIR, f"{fallback_name}.svg")

    if not os.path.exists(icon_path):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        return pix

    try:
        with open(icon_path, "r", encoding="utf-8") as f:
            svg_content = f.read()

        if color is not None:
            svg_content = svg_content.replace("currentColor", color.name())

        renderer = QSvgRenderer(svg_content.encode("utf-8"))
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()

        return pix
    except Exception:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        return pix


def get_svg_icon(
    name: str,
    size: int = 24,
    color: Optional[QColor] = None,
    fallback_name: str = "default_media",
) -> QIcon:
    """Load an SVG icon from assets/icons/{name}.svg and return QIcon wrapper."""
    pixmap = get_svg_pixmap(name, size=size, color=color, fallback_name=fallback_name)
    return QIcon(pixmap)


def extract_dominant_color(
    art_bytes: Optional[bytes],
    fallback: QColor = COLOR_ACCENT_GREEN,
) -> QColor:
    """Extract a vibrant dominant accent color from raw image bytes using PySide6 QImage only.
    
    Downsamples image to 16x16 in memory and samples pixel colors with saturation/luminance filtering.
    Zero third-party dependencies required.
    """
    if not art_bytes:
        return fallback

    try:
        image = QImage()
        if not image.loadFromData(art_bytes):
            return fallback

        small = image.scaled(16, 16, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        best_color = fallback
        best_score = -1.0

        for y in range(16):
            for x in range(16):
                c = small.pixelColor(x, y)
                h, s, v, _ = c.getHsvF()
                if s > 0.25 and 0.2 < v < 0.95:
                    score = s * 1.5 + (1.0 - abs(v - 0.6))
                    if score > best_score:
                        best_score = score
                        best_color = c

        return best_color
    except Exception:
        return fallback


def get_status_badge_style(status: PlaybackStatus) -> tuple[str, str, str]:
    """Return tuple of (display_text, text_hex, bg_hex) for a given PlaybackStatus."""
    if status == PlaybackStatus.PLAYING:
        return (PlaybackStatus.PLAYING.value, "#00FF7F", "#0A2919")
    elif status == PlaybackStatus.PAUSED:
        return (PlaybackStatus.PAUSED.value, "#C1121C", "#2E0A0D")
    elif status == PlaybackStatus.STOPPED:
        return (PlaybackStatus.STOPPED.value, "#C1121C", "#2E0A0D")
    elif status == PlaybackStatus.CLOSED:
        return (PlaybackStatus.CLOSED.value, "#8A8A8A", "#141414")
    elif status == PlaybackStatus.UNKNOWN:
        return (PlaybackStatus.UNKNOWN.value, "#8A8A8A", "#141414")
    else:
        return (status.value, "#8A8A8A", "#141414")



def get_button_stylesheet() -> str:
    """Return QSS stylesheet for transport control buttons matching dashboard design language."""
    return (
        "QPushButton {"
        "  background-color: #222222;"
        "  color: #FFFFFF;"
        "  border: 1px solid #2A2A2A;"
        "  border-radius: 4px;"
        "  font-size: 12px;"
        "  font-weight: bold;"
        "}"
        "QPushButton:hover {"
        "  background-color: #2A2A2A;"
        "  color: #FFFFFF;"
        "  border: 1px solid #00FF7F;"
        "}"
        "QPushButton:pressed {"
        "  background-color: #333333;"
        "  color: #00FF7F;"
        "}"
        "QPushButton:disabled {"
        "  color: #555555;"
        "  background-color: #141414;"
        "  border: 1px solid #222222;"
        "}"
    )


def get_slider_stylesheet(accent: QColor = COLOR_ACCENT_GREEN) -> str:
    """Return QSS stylesheet for progress slider using specified accent color."""
    accent_hex = accent.name()
    return (
        f"QSlider::groove:horizontal {{ height: 4px; background: #222222; border-radius: 2px; }}"
        f"QSlider::sub-page:horizontal {{ background: {accent_hex}; border-radius: 2px; }}"
        f"QSlider::handle:horizontal {{ background: #FFFFFF; width: 10px; margin-top: -3px; margin-bottom: -3px; border-radius: 5px; }}"
        f"QSlider::handle:horizontal:hover {{ background: {accent_hex}; }}"
        f"QSlider::disabled {{ opacity: 0.4; }}"
    )
