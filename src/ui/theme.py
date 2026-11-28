import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor,
    QConicalGradient,
    QGradient,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtSvg import QSvgRenderer

from src.core.models import PlaybackStatus

# --- Design Tokens & Centralized Color Architecture ---
COLOR_BG_ISLAND = QColor("#000000")  # Pure Black baseline for capsule & expanded card
COLOR_BORDER_ISLAND = QColor("#000000")  # Pure Black border baseline
COLOR_NOTCH_SHELL = QColor("#0B0B0D")  # DeskNotch obsidian surface fill
COLOR_NOTCH_BORDER = QColor(255, 255, 255, 22)  # DeskNotch subtle top-edge light catch
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


def ensure_bright_accent_color(color: Optional[QColor]) -> QColor:
    """Ensure an accent color is delightfully bright, luminous, and legible against dark backgrounds.
    
    Transforms dark, muddy, or low-contrast shades into vibrant, high-luminance tones
    while strictly preserving the album art's artistic hue.
    """
    if not color or not color.isValid():
        return COLOR_ACCENT_GREEN
    h, s, v, a = color.getHsvF()
    if h < 0:
        # Grayscale
        return COLOR_ACCENT_GREEN

    # If the color already has high brightness (V >= 0.88) and healthy saturation, keep it
    if v >= 0.88 and s >= 0.40:
        return color

    # For dark, muddy, or low-luminance colors, boost value to 0.96-1.0 while keeping hue intact
    bright_s = max(0.45, min(0.85, s if s >= 0.20 else 0.80))
    bright_v = max(0.96, min(1.0, v + 0.50))

    bright_col = QColor()
    bright_col.setHsvF(h, bright_s, bright_v, a)
    return bright_col


def extract_dominant_color(
    art_bytes: Optional[bytes],
    fallback: QColor = COLOR_ACCENT_GREEN,
) -> QColor:
    """Extract a vibrant dominant accent color from raw image bytes using PySide6 QImage only.
    
    Downsamples image to 16x16 in memory and samples pixel colors with saturation/luminance filtering.
    Zero third-party dependencies required. Always returns a bright, luminous color.
    """
    if not art_bytes:
        return fallback

    try:
        image = QImage()
        if not image.loadFromData(art_bytes):
            return fallback

        small = image.scaled(16, 16, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        best_color = None
        best_score = -1.0

        for y in range(16):
            for x in range(16):
                c = small.pixelColor(x, y)
                h, s, v, _ = c.getHsvF()
                if s > 0.20 and v > 0.25:
                    score = s * 1.5 + v * 1.2
                    if score > best_score:
                        best_score = score
                        best_color = c

        if best_color is not None:
            return ensure_bright_accent_color(best_color)
        return fallback
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
        f"QSlider::groove:horizontal {{ height: 3px; background: rgba(255, 255, 255, 0.16); border-radius: 1px; }}"
        f"QSlider::sub-page:horizontal {{ background: {accent_hex}; border-radius: 1px; }}"
        f"QSlider::handle:horizontal {{ background: #FFFFFF; width: 10px; height: 10px; margin-top: -3.5px; margin-bottom: -3.5px; border-radius: 5px; }}"
        f"QSlider::handle:horizontal:hover {{ background: #FFFFFF; width: 12px; height: 12px; margin-top: -4.5px; margin-bottom: -4.5px; border-radius: 6px; }}"
        f"QSlider::disabled {{ opacity: 0.4; }}"
    )


def get_desknotch_play_button_stylesheet() -> str:
    """Return QSS for DeskNotch's signature solid white circular Play/Pause disc button."""
    return (
        "QPushButton {"
        "  background-color: #FFFFFF;"
        "  color: #000000;"
        "  border: none;"
        "  border-radius: 17px;"
        "}"
        "QPushButton:hover {"
        "  background-color: rgba(255, 255, 255, 0.9);"
        "}"
        "QPushButton:pressed {"
        "  background-color: rgba(255, 255, 255, 0.78);"
        "}"
        "QPushButton:disabled {"
        "  background-color: rgba(255, 255, 255, 0.3);"
        "}"
    )


def get_desknotch_icon_button_stylesheet() -> str:
    """Return QSS for minimalist DeskNotch circular hover transport/dock buttons."""
    return (
        "QPushButton {"
        "  background-color: transparent;"
        "  color: rgba(255, 255, 255, 0.65);"
        "  border: none;"
        "  border-radius: 13px;"
        "}"
        "QPushButton:hover {"
        "  background-color: rgba(255, 255, 255, 0.10);"
        "  color: #FFFFFF;"
        "}"
        "QPushButton:pressed {"
        "  background-color: rgba(255, 255, 255, 0.18);"
        "}"
        "QPushButton:checked {"
        "  background-color: transparent;"
        "  color: #FFFFFF;"
        "}"
        "QPushButton:checked:hover {"
        "  background-color: rgba(255, 255, 255, 0.10);"
        "}"
    )


def create_rounded_pixmap(pixmap: QPixmap, size: int, radius: float = 12.0) -> QPixmap:
    """Return a crisp aspect-filled QPixmap clipped to anti-aliased rounded corners."""
    if pixmap.isNull() or size <= 0:
        out = QPixmap(max(1, size), max(1, size))
        out.fill(Qt.GlobalColor.transparent)
        return out

    scaled = pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    # Center crop if aspect ratio expanded past target square
    if scaled.width() > size or scaled.height() > size:
        x_off = max(0, (scaled.width() - size) // 2)
        y_off = max(0, (scaled.height() - size) // 2)
        scaled = scaled.copy(x_off, y_off, size, size)

    rounded = QPixmap(size, size)
    rounded.fill(Qt.GlobalColor.transparent)

    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return rounded


# --- Gradient Presets, Styles & Custom Banner Rendering ---

GRADIENT_PRESETS: Dict[str, Tuple[str, str, str]] = {
    "Aurora": ("#071A20", "#0F5257", "#1B3B6F"),
    "Cyber Mint": ("#041410", "#0A4F3C", "#00B86B"),
    "Midnight Neon": ("#0F0C29", "#302B63", "#24243E"),
    "Sunset Ember": ("#230812", "#8E1D41", "#D96B27"),
    "Royal Velvet": ("#14072E", "#441A75", "#7B2CBF"),
    "Deep Ocean": ("#071426", "#113F7A", "#2563EB"),
    "Rose Quartz": ("#1D0B18", "#5C1B47", "#B84A7A"),
    "Obsidian Steel": ("#09090C", "#1B1E28", "#323748"),
}

GRADIENT_STYLES: Tuple[Tuple[str, str], ...] = (
    ("linear_diag", "Diagonal (Top-Left → Bottom-Right)"),
    ("linear_h", "Horizontal (Left → Right)"),
    ("linear_v", "Vertical (Top → Bottom)"),
    ("linear_diag_rev", "Reverse Diagonal (Bottom-Left → Top-Right)"),
    ("radial", "Radial Glow (Center Outward)"),
    ("conic", "Conic (Sweep Around Center)"),
    ("mesh", "Dual-Tone Mesh Glow"),
)

IMAGE_ALIGNMENTS: Tuple[Tuple[str, str], ...] = (
    ("center", "Center Crop"),
    ("top", "Top Edge Focus"),
    ("bottom", "Bottom Edge Focus"),
)


@dataclass(frozen=True)
class NotchAppearance:
    """Immutable snapshot of visual background, gradient, border, and banner settings."""

    bg_mode: str = "solid"
    bg_color: QColor = field(default_factory=lambda: QColor("#000000"))
    border_color: QColor = field(default_factory=lambda: QColor("#000000"))
    gradient_preset: str = "Aurora"
    gradient_style: str = "linear_diag"
    gradient_color_1: QColor = field(default_factory=lambda: QColor("#071A20"))
    gradient_color_2: Optional[QColor] = field(default_factory=lambda: QColor("#0F5257"))
    gradient_color_3: QColor = field(default_factory=lambda: QColor("#1B3B6F"))
    collapsed_image_path: str = ""
    expanded_image_path: str = ""
    image_dim_percent: int = 35
    image_alignment: str = "center"

    @classmethod
    def from_settings(cls, settings_manager) -> "NotchAppearance":
        """Build NotchAppearance safely from SettingsManager or mock/stub objects."""
        def _read_str(method_name: str, default: str) -> str:
            fn = getattr(settings_manager, method_name, None)
            if not callable(fn):
                return default
            val = fn()
            return val if isinstance(val, str) else default

        bg_hex = _read_str("get_notch_bg_color", "#000000")
        border_hex = _read_str("get_notch_border_color", "#000000")
        bg_mode = _read_str("get_appearance_bg_mode", "solid").lower()
        if bg_mode not in ("solid", "gradient", "image"):
            bg_mode = "solid"
        preset = _read_str("get_gradient_preset", "Aurora")
        style = _read_str("get_gradient_style", "linear_diag").lower()

        g1, g2, g3 = ("#071A20", "#0F5257", "#1B3B6F")
        colors_fn = getattr(settings_manager, "get_gradient_colors", None)
        if callable(colors_fn):
            raw_colors = colors_fn()
            if (
                isinstance(raw_colors, (tuple, list))
                and len(raw_colors) == 3
                and all(isinstance(x, str) for x in raw_colors)
            ):
                g1, g2, g3 = raw_colors[0], raw_colors[1], raw_colors[2]

        c1 = QColor(g1) if QColor(g1).isValid() else QColor("#071A20")
        c2 = QColor(g2) if (g2 and QColor(g2).isValid()) else None
        c3 = QColor(g3) if QColor(g3).isValid() else QColor("#1B3B6F")

        collapsed_img = _read_str("get_collapsed_image_path", "")
        expanded_img = _read_str("get_expanded_image_path", "")
        dim_pct = 35
        dim_fn = getattr(settings_manager, "get_image_dim_percent", None)
        if callable(dim_fn):
            raw_dim = dim_fn()
            if isinstance(raw_dim, (int, float)) and not isinstance(raw_dim, bool):
                dim_pct = int(raw_dim)
        align = _read_str("get_image_alignment", "center").lower()
        if align not in ("center", "top", "bottom"):
            align = "center"

        return cls(
            bg_mode=bg_mode,
            bg_color=QColor(bg_hex) if QColor(bg_hex).isValid() else QColor("#000000"),
            border_color=QColor(border_hex) if QColor(border_hex).isValid() else QColor("#000000"),
            gradient_preset=preset,
            gradient_style=style,
            gradient_color_1=c1,
            gradient_color_2=c2,
            gradient_color_3=c3,
            collapsed_image_path=collapsed_img,
            expanded_image_path=expanded_img,
            image_dim_percent=max(0, min(85, dim_pct)),
            image_alignment=align,
        )


_RAW_BANNER_CACHE: Dict[Tuple[str, int], QPixmap] = {}
_SCALED_BANNER_CACHE: Dict[Tuple[str, int, int, int, str], QPixmap] = {}
_MAX_BANNER_CACHE_ENTRIES = 24


def invalidate_banner_cache() -> None:
    """Clear cached custom banner QPixmaps."""
    _RAW_BANNER_CACHE.clear()
    _SCALED_BANNER_CACHE.clear()


def get_scaled_banner_pixmap(
    image_path: str,
    width: int,
    height: int,
    alignment: str = "center",
) -> Optional[QPixmap]:
    """Load, cover-scale, and crop a banner image for the target widget size, using an in-memory cache."""
    if not image_path or width <= 0 or height <= 0:
        return None

    try:
        mtime_ns = os.stat(image_path).st_mtime_ns
    except OSError:
        return None

    scaled_key = (image_path, mtime_ns, width, height, alignment)
    cached_scaled = _SCALED_BANNER_CACHE.get(scaled_key)
    if cached_scaled is not None:
        return cached_scaled

    raw_key = (image_path, mtime_ns)
    raw_pix = _RAW_BANNER_CACHE.get(raw_key)
    if raw_pix is None:
        loaded = QPixmap(image_path)
        if loaded.isNull():
            return None
        if len(_RAW_BANNER_CACHE) >= _MAX_BANNER_CACHE_ENTRIES:
            _RAW_BANNER_CACHE.clear()
        _RAW_BANNER_CACHE[raw_key] = loaded
        raw_pix = loaded

    scaled = raw_pix.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x_off = max(0, (scaled.width() - width) // 2)
    extra_h = max(0, scaled.height() - height)
    if alignment == "top":
        y_off = 0
    elif alignment == "bottom":
        y_off = extra_h
    else:
        y_off = extra_h // 2

    cropped = scaled.copy(x_off, y_off, width, height)
    if len(_SCALED_BANNER_CACHE) >= _MAX_BANNER_CACHE_ENTRIES:
        _SCALED_BANNER_CACHE.clear()
    _SCALED_BANNER_CACHE[scaled_key] = cropped
    return cropped


def build_notch_gradient(
    rect: QRectF,
    style: str,
    color_1: QColor,
    color_2: Optional[QColor],
    color_3: QColor,
) -> QGradient:
    """Create configured QGradient (linear directions, radial, conic sweep, or mesh base) over rect."""
    c1 = color_1 if color_1.isValid() else COLOR_BG_ISLAND
    c3 = color_3 if color_3.isValid() else c1
    c2 = color_2 if (color_2 is not None and color_2.isValid()) else None

    if style == "linear_h":
        grad: QGradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    elif style == "linear_v":
        grad = QLinearGradient(rect.center().x(), rect.top(), rect.center().x(), rect.bottom())
    elif style == "linear_diag_rev":
        grad = QLinearGradient(rect.bottomLeft(), rect.topRight())
    elif style == "radial":
        grad = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.65)
    elif style == "conic":
        grad = QConicalGradient(rect.center(), 45.0)
        if c2 is not None:
            grad.setColorAt(0.0, c1)
            grad.setColorAt(0.35, c2)
            grad.setColorAt(0.70, c3)
            grad.setColorAt(1.0, c1)
        else:
            grad.setColorAt(0.0, c1)
            grad.setColorAt(0.5, c3)
            grad.setColorAt(1.0, c1)
        return grad
    else:
        # "linear_diag" or base layer of "mesh"
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())

    if c2 is not None:
        grad.setColorAt(0.0, c1)
        grad.setColorAt(0.5, c2)
        grad.setColorAt(1.0, c3)
    else:
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c3)
    return grad


def paint_notch_surface(
    painter: QPainter,
    rect: QRectF,
    path: QPainterPath,
    inner_path: QPainterPath,
    appearance: NotchAppearance,
    is_expanded: bool = False,
    ambient_accent: Optional[QColor] = None,
) -> None:
    """Render solid/gradient/custom-banner shell fill, sheen, ambient glow, and crisp border stroke."""
    # 1. Base solid fill (guarantees opaque substrate and seamless fallback)
    painter.fillPath(path, appearance.bg_color)

    has_rendered_banner = False
    if appearance.bg_mode == "gradient":
        grad = build_notch_gradient(
            rect,
            appearance.gradient_style,
            appearance.gradient_color_1,
            appearance.gradient_color_2,
            appearance.gradient_color_3,
        )
        painter.fillPath(path, grad)
        if appearance.gradient_style == "mesh":
            painter.save()
            painter.setClipPath(path)
            accent_stop = appearance.gradient_color_2 or appearance.gradient_color_3
            blob_a = QColor(accent_stop)
            blob_a.setAlpha(175)
            blob_b = QColor(accent_stop)
            blob_b.setAlpha(0)
            blob_center_x = rect.left() + rect.width() * 0.78
            blob_center_y = rect.top() + rect.height() * 0.25
            mesh_glow = QRadialGradient(blob_center_x, blob_center_y, max(rect.width(), rect.height()) * 0.55)
            mesh_glow.setColorAt(0.0, blob_a)
            mesh_glow.setColorAt(1.0, blob_b)
            painter.fillRect(rect, mesh_glow)
            painter.restore()

    elif appearance.bg_mode == "image":
        banner_path = appearance.expanded_image_path if is_expanded else appearance.collapsed_image_path
        aligned_rect = rect.toAlignedRect()
        target_w = max(1, aligned_rect.width())
        target_h = max(1, aligned_rect.height())
        banner_pix = get_scaled_banner_pixmap(
            banner_path,
            target_w,
            target_h,
            alignment=appearance.image_alignment,
        )
        if banner_pix is not None and not banner_pix.isNull():
            has_rendered_banner = True
            painter.save()
            painter.setClipPath(path)
            painter.drawPixmap(aligned_rect, banner_pix)
            if appearance.image_dim_percent > 0:
                scrim_alpha = int(round(255.0 * min(85, appearance.image_dim_percent) / 100.0))
                painter.fillRect(rect, QColor(0, 0, 0, scrim_alpha))
            painter.restore()

    # 2. Translucent frost top sheen
    sheen = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
    if has_rendered_banner:
        sheen.setColorAt(0.0, QColor(255, 255, 255, 10))
        sheen.setColorAt(0.5, QColor(255, 255, 255, 3))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
    else:
        sheen.setColorAt(0.0, QColor(255, 255, 255, 14))
        sheen.setColorAt(0.45, QColor(255, 255, 255, 5))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 2))
    painter.fillPath(path, sheen)

    # 3. Radial cover glow anchored behind left artwork (when expanded)
    if is_expanded and ambient_accent is not None and ambient_accent.isValid():
        painter.save()
        painter.setClipPath(path)
        glow_cx = rect.left() + 68.0
        glow_cy = rect.top() + 72.0
        glow_grad = QRadialGradient(glow_cx, glow_cy, float(rect.width() * 0.65))
        c1 = QColor(ambient_accent)
        c2 = QColor(ambient_accent)
        if has_rendered_banner or appearance.bg_mode == "gradient":
            c1.setAlpha(38)
            c2.setAlpha(8)
        else:
            c1.setAlpha(74)
            c2.setAlpha(18)
        glow_grad.setColorAt(0.0, c1)
        glow_grad.setColorAt(0.55, c2)
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, glow_grad)
        painter.restore()

    # 4. Crisp inner light-catch + outer border
    if appearance.border_color == COLOR_BORDER_ISLAND:
        painter.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
        painter.drawPath(inner_path)
        pen_width = 1.0
    else:
        pen_width = 1.5

    painter.setPen(QPen(appearance.border_color, pen_width))
    painter.drawPath(path)
