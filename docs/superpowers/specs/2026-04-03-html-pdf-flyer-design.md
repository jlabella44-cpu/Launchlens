# HTML-to-PDF Flyer Generator Design

**Date:** 2026-04-03
**Status:** Approved

## Goal

Replace the MockTemplateProvider with a real HTML-to-PDF flyer generator that produces professional listing flyers without external API dependencies. Supports multiple rotating styles.

## Architecture

A new `HtmlTemplateProvider` implements `TemplateProvider.render(template_id, data) -> bytes`. It uses Jinja2 for HTML templating and `weasyprint` for PDF conversion. Three built-in styles rotate automatically.

## Files

```
src/listingjet/providers/
  html_template.py              # HtmlTemplateProvider class
  templates/
    modern.html                 # Clean white, big hero photo, minimal text
    bold.html                   # Strong brand colors, prominent agent/logo
    classic.html                # Traditional real estate flyer layout
    base.css                    # Shared typography, spacing, print layout
src/listingjet/providers/factory.py  # Updated: HtmlTemplateProvider as default
tests/test_providers/test_html_template.py  # Tests
```

## HtmlTemplateProvider

```python
class HtmlTemplateProvider(TemplateProvider):
    """Renders listing flyers as PDF from HTML/CSS templates."""

    STYLES = ["modern", "bold", "classic"]

    async def render(self, template_id: str, data: dict) -> bytes:
        # template_id selects style: "modern", "bold", "classic", or "auto"
        # "auto" cycles based on listing_id hash
        # Returns PDF bytes via weasyprint
```

### Template Selection

- `template_id == "modern"` / `"bold"` / `"classic"` — uses that style directly
- `template_id == "auto"` or any unrecognized value — deterministically picks a style based on `hash(data["listing_id"]) % 3` so the same listing always gets the same style
- The `CANVA_DEFAULT_TEMPLATE_ID` config value (when set to a style name) flows through unchanged

### Data Contract

The `data` dict passed to `render()` contains (from `BrandAgent`):

```python
{
    "listing_id": str,
    "address": {"street": str, "city": str, "state": str, "zip": str},
    "metadata": {"beds": int, "baths": int, "sqft": int, "price": float},
    "hero_image_url": str | None,       # presigned S3 URL
    "hero_asset_id": str | None,
    "primary_color": str,               # hex, e.g. "#2563EB"
    "secondary_color": str | None,
    "agent_name": str | None,
    "brokerage_name": str | None,
    "logo_url": str | None,             # presigned S3 URL
    "font": str | None,
}
```

### Template Design

All templates are single-page, print-ready (US Letter 8.5x11" portrait).

**modern.html** — Clean & Modern
- White background, full-width hero photo (top 40%)
- Large address and price below hero
- Specs row: beds | baths | sqft
- Brand bar at bottom: agent name, brokerage, logo
- Primary color used for accent lines only

**bold.html** — Bold & Branded
- Primary color as header band with address/price in white
- Hero photo center (60% width), rounded corners
- Specs in colored badges
- Agent name + logo + brokerage in colored footer band
- Secondary color for spec badges

**classic.html** — Traditional
- Thin border frame, serif-adjacent typography
- Hero photo left half, details right half (side-by-side)
- Clean property details list
- Agent/brokerage info at bottom with logo
- Primary color for headings only

**base.css** — Shared
- `@page` rules for US Letter, margins
- Font stacks (system fonts, no external loads)
- Utility classes for colors, spacing
- Print-specific resets

### Hero Image Handling

The `hero_image_url` is a presigned S3 URL. For `weasyprint` to render it, the image must be fetchable. `weasyprint` handles external URLs natively — it will fetch the image during PDF generation.

If `hero_image_url` is None, templates show a gradient placeholder with the address overlaid.

## Factory Update

```python
def get_template_provider() -> TemplateProvider:
    if settings.use_mock_providers:
        from .mock import MockTemplateProvider
        return MockTemplateProvider()
    if settings.canva_api_key:
        from .canva import CanvaTemplateProvider
        return CanvaTemplateProvider(api_key=settings.canva_api_key, llm_provider=get_llm_provider())
    # Default: self-hosted HTML-to-PDF (no external API needed)
    from .html_template import HtmlTemplateProvider
    return HtmlTemplateProvider()
```

Priority: Mock (tests) → Canva (if configured) → HTML-to-PDF (default)

## Dependencies

- `weasyprint` — HTML/CSS to PDF. Pure Python, uses system libraries (cairo, pango, gdk-pixbuf). Install: `pip install weasyprint`
- `jinja2` — already in project (FastAPI dependency)

### weasyprint System Dependencies

On the Docker image (Debian-based), needs: `libcairo2`, `libpango-1.0-0`, `libgdk-pixbuf-2.0-0`, `libffi-dev`. These are common and small.

## Testing

- Test each template renders without error
- Test "auto" selection is deterministic
- Test missing hero_image_url produces a placeholder
- Test brand colors are applied
- Test output is valid PDF (starts with `%PDF`)
- Test factory returns HtmlTemplateProvider when no Canva key

## What's NOT Changing

- TemplateProvider interface
- BrandAgent code (it just calls render())
- Canva provider (stays as optional upgrade)
- Mock provider (stays for tests)
