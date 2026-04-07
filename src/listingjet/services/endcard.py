"""Generate branded video end-cards using Pillow.

Creates a static PNG with the agent's BrandKit data (logo, name, brokerage,
colors) that can be concatenated to the end of a property tour video via ffmpeg.
"""
import io
import logging

logger = logging.getLogger(__name__)

# End-card dimensions match standard video output
ENDCARD_WIDTH = 1280
ENDCARD_HEIGHT = 720
ENDCARD_DURATION = 5  # seconds


def _draw_gradient(img, color_top: tuple[int, int, int], color_bottom: tuple[int, int, int]):
    """Draw a vertical gradient from color_top to color_bottom."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        ratio = y / h
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _darken(color: tuple[int, int, int], factor: float = 0.4) -> tuple[int, int, int]:
    """Darken a color by a factor (0 = black, 1 = unchanged)."""
    return (int(color[0] * factor), int(color[1] * factor), int(color[2] * factor))


def _lighten(color: tuple[int, int, int], factor: float = 0.3) -> tuple[int, int, int]:
    """Lighten a color toward white by a factor."""
    return (
        int(color[0] + (255 - color[0]) * factor),
        int(color[1] + (255 - color[1]) * factor),
        int(color[2] + (255 - color[2]) * factor),
    )


def generate_endcard(
    brokerage_name: str = "",
    agent_name: str = "",
    primary_color: str = "#2563EB",
    logo_bytes: bytes | None = None,
) -> bytes:
    """Generate a branded end-card PNG with gradient background.

    Returns PNG bytes ready for ffmpeg concatenation.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        base_color = _hex_to_rgb(primary_color)
        gradient_top = _darken(base_color, 0.6)
        gradient_bottom = _darken(base_color, 0.2)

        img = Image.new("RGB", (ENDCARD_WIDTH, ENDCARD_HEIGHT))
        _draw_gradient(img, gradient_top, gradient_bottom)
        draw = ImageDraw.Draw(img)

        # Subtle accent line across top third
        accent_color = _lighten(base_color, 0.2)
        accent_y = ENDCARD_HEIGHT // 3 - 40
        draw.line(
            [(ENDCARD_WIDTH // 4, accent_y), (3 * ENDCARD_WIDTH // 4, accent_y)],
            fill=accent_color, width=2,
        )

        # Load fonts — try multiple paths for cross-platform compatibility
        font_paths_bold = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
        font_paths_regular = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]

        def _load_font(paths, size):
            for p in paths:
                try:
                    return ImageFont.truetype(p, size)
                except OSError:
                    continue
            return ImageFont.load_default()

        font_brokerage = _load_font(font_paths_bold, 52)
        font_agent = _load_font(font_paths_regular, 30)
        font_tagline = _load_font(font_paths_regular, 18)

        # Layout: vertically centered content block
        content_items = []
        if logo_bytes:
            content_items.append(("logo", None))
        if brokerage_name:
            content_items.append(("brokerage", brokerage_name))
        if agent_name:
            content_items.append(("agent", agent_name))

        # Calculate total content height for centering
        total_h = 0
        if logo_bytes:
            total_h += 130  # logo height + spacing
        if brokerage_name:
            total_h += 70
        if agent_name:
            total_h += 50

        y_cursor = (ENDCARD_HEIGHT - total_h) // 2

        # Logo (centered)
        if logo_bytes:
            try:
                logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
                max_logo_h = 100
                ratio = min(360 / logo.width, max_logo_h / logo.height)
                logo = logo.resize(
                    (int(logo.width * ratio), int(logo.height * ratio)),
                    Image.LANCZOS,
                )
                logo_x = (ENDCARD_WIDTH - logo.width) // 2
                img.paste(logo, (logo_x, y_cursor), logo)
                y_cursor += logo.height + 30
            except Exception:
                pass

        # Brokerage name (large, white, centered)
        if brokerage_name:
            bbox = draw.textbbox((0, 0), brokerage_name, font=font_brokerage)
            text_w = bbox[2] - bbox[0]
            draw.text(
                ((ENDCARD_WIDTH - text_w) // 2, y_cursor),
                brokerage_name,
                fill=(255, 255, 255),
                font=font_brokerage,
            )
            y_cursor += 70

        # Agent name (lighter, smaller)
        if agent_name:
            bbox = draw.textbbox((0, 0), agent_name, font=font_agent)
            text_w = bbox[2] - bbox[0]
            draw.text(
                ((ENDCARD_WIDTH - text_w) // 2, y_cursor),
                agent_name,
                fill=(255, 255, 255, 200),
                font=font_agent,
            )

        # Bottom accent line
        draw.line(
            [(ENDCARD_WIDTH // 4, ENDCARD_HEIGHT - 80), (3 * ENDCARD_WIDTH // 4, ENDCARD_HEIGHT - 80)],
            fill=accent_color, width=1,
        )

        # Tagline at bottom
        tagline = "Powered by ListingJet"
        bbox = draw.textbbox((0, 0), tagline, font=font_tagline)
        text_w = bbox[2] - bbox[0]
        draw.text(
            ((ENDCARD_WIDTH - text_w) // 2, ENDCARD_HEIGHT - 55),
            tagline,
            fill=_lighten(base_color, 0.5),
            font=font_tagline,
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    except ImportError:
        logger.warning("Pillow not available for end-card generation")
        return b""


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB to (R, G, B) tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (37, 99, 235)  # Default blue
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
