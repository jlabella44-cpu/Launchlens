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


def generate_endcard(
    brokerage_name: str = "",
    agent_name: str = "",
    primary_color: str = "#2563EB",
    logo_bytes: bytes | None = None,
) -> bytes:
    """Generate a branded end-card PNG.

    Returns PNG bytes ready for ffmpeg concatenation.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Parse hex color
        bg_color = _hex_to_rgb(primary_color)
        text_color = (255, 255, 255)

        img = Image.new("RGB", (ENDCARD_WIDTH, ENDCARD_HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        # Load font
        try:
            font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
            )
            font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28
            )
        except OSError:
            font_large = ImageFont.load_default()
            font_small = font_large

        y_cursor = ENDCARD_HEIGHT // 3

        # Logo (centered, above text)
        if logo_bytes:
            try:
                logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
                max_logo_h = 120
                ratio = min(400 / logo.width, max_logo_h / logo.height)
                logo = logo.resize((int(logo.width * ratio), int(logo.height * ratio)))
                logo_x = (ENDCARD_WIDTH - logo.width) // 2
                logo_y = y_cursor - logo.height - 20
                img.paste(logo, (logo_x, logo_y), logo)
            except Exception:
                pass  # Skip logo on failure

        # Brokerage name (large, centered)
        if brokerage_name:
            bbox = draw.textbbox((0, 0), brokerage_name, font=font_large)
            text_w = bbox[2] - bbox[0]
            draw.text(
                ((ENDCARD_WIDTH - text_w) // 2, y_cursor),
                brokerage_name,
                fill=text_color,
                font=font_large,
            )
            y_cursor += 70

        # Agent name (smaller, centered)
        if agent_name:
            bbox = draw.textbbox((0, 0), agent_name, font=font_small)
            text_w = bbox[2] - bbox[0]
            draw.text(
                ((ENDCARD_WIDTH - text_w) // 2, y_cursor),
                agent_name,
                fill=text_color,
                font=font_small,
            )
            y_cursor += 50

        # Tagline
        tagline = "Powered by ListingJet"
        bbox = draw.textbbox((0, 0), tagline, font=font_small)
        text_w = bbox[2] - bbox[0]
        draw.text(
            ((ENDCARD_WIDTH - text_w) // 2, ENDCARD_HEIGHT - 60),
            tagline,
            fill=(255, 255, 255, 180),
            font=font_small,
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
