"""UI design system tokens, QSS style generators, and Qt-only color extraction for MediaDock."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage

from src.core.models import PlaybackStatus

# --- Design Tokens (Catppuccin Mocha Palette) ---
COLOR_BG_BASE = QColor("#1E1E2E")
COLOR_BG_MANTLE = QColor("#181825")
COLOR_BG_SURFACE = QColor("#313244")
COLOR_BORDER = QColor("#45475A")

COLOR_TEXT_PRIMARY = QColor("#FFFFFF")
COLOR_TEXT_SECONDARY = QColor("#A6ADC8")
COLOR_TEXT_MUTED = QColor("#6C7086")

COLOR_ACCENT_GREEN = QColor("#A6E3A1")
COLOR_ACCENT_YELLOW = QColor("#F9E2AF")
COLOR_ACCENT_RED = QColor("#F38BA8")
COLOR_ACCENT_BLUE = QColor("#89B4FA")


def extract_dominant_color(
    art_bytes: Optional[bytes],
    fallback: QColor = COLOR_ACCENT_BLUE,
) -> QColor:
    """Extract a vibrant dominant accent color from raw image bytes using PySide6 QImage only.
    
    Downsamples image to 16x16 in memory and samples pixel colors with saturation/luminance filtering.
    Zero third-party dependencies required.
    """
    if not art_bytes:
        return fallback

    img = QImage()
    if not img.loadFromData(art_bytes) or img.isNull():
        return fallback

    # Downsample to 16x16 thumbnail for ultra-fast sampling (<1ms)
    scaled = img.scaled(
        16,
        16,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    best_color = fallback
    max_score = -1.0

    sum_r, sum_g, sum_b, count = 0, 0, 0, 0

    for x in range(scaled.width()):
        for y in range(scaled.height()):
            color = scaled.pixelColor(x, y)
            r, g, b, _ = color.getRgb()

            # Calculate brightness/luminance
            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

            # Skip extreme darks and extreme bright whites
            if luminance < 35 or luminance > 225:
                continue

            sum_r += r
            sum_g += g
            sum_b += b
            count += 1

            # Score based on HSV saturation and mid-tone luminance
            hsv_sat = color.hsvSaturationF()
            score = hsv_sat * (1.0 - abs(luminance - 128.0) / 128.0)

            if score > max_score:
                max_score = score
                best_color = color

    if max_score > 0.15:
        return best_color

    if count > 0:
        return QColor(sum_r // count, sum_g // count, sum_b // count)

    return fallback


def get_status_badge_style(status: PlaybackStatus) -> tuple[str, str, str]:
    """Return tuple of (display_text, text_hex, bg_hex) for a given PlaybackStatus."""
    if status == PlaybackStatus.PLAYING:
        return (PlaybackStatus.PLAYING.value, "#A6E3A1", "#1E2E28")
    elif status == PlaybackStatus.PAUSED:
        return (PlaybackStatus.PAUSED.value, "#F9E2AF", "#2E2A1E")
    elif status == PlaybackStatus.STOPPED:
        return (PlaybackStatus.STOPPED.value, "#F38BA8", "#2E1E22")
    elif status == PlaybackStatus.CLOSED:
        return (PlaybackStatus.CLOSED.value, "#6C7086", "#181825")
    elif status == PlaybackStatus.UNKNOWN:
        return (PlaybackStatus.UNKNOWN.value, "#6C7086", "#181825")
    else:
        return (status.value, "#6C7086", "#181825")



def get_button_stylesheet() -> str:
    """Return QSS stylesheet for transport control buttons."""
    return (
        "QPushButton {"
        "  background-color: #313244;"
        "  color: #CDD6F4;"
        "  border: 1px solid #45475A;"
        "  border-radius: 4px;"
        "  font-size: 12px;"
        "  font-weight: bold;"
        "}"
        "QPushButton:hover {"
        "  background-color: #45475A;"
        "  color: #FFFFFF;"
        "}"
        "QPushButton:pressed {"
        "  background-color: #585B70;"
        "  color: #89B4FA;"
        "}"
        "QPushButton:disabled {"
        "  color: #585B70;"
        "  background-color: #181825;"
        "  border: 1px solid #313244;"
        "}"
    )


def get_slider_stylesheet(accent: QColor = COLOR_ACCENT_BLUE) -> str:
    """Return QSS stylesheet for progress slider using specified accent color."""
    accent_hex = accent.name()
    return (
        f"QSlider::groove:horizontal {{ height: 4px; background: #313244; border-radius: 2px; }}"
        f"QSlider::sub-page:horizontal {{ background: {accent_hex}; border-radius: 2px; }}"
        f"QSlider::handle:horizontal {{ background: #CDD6F4; width: 10px; margin-top: -3px; margin-bottom: -3px; border-radius: 5px; }}"
        f"QSlider::handle:horizontal:hover {{ background: {accent_hex}; }}"
        f"QSlider::disabled {{ opacity: 0.4; }}"
    )
