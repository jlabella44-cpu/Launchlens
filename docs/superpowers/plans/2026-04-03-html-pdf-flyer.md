# HTML-to-PDF Flyer Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-hosted HTML-to-PDF flyer generator with 3 rotating styles that replaces MockTemplateProvider as the default.

**Architecture:** `HtmlTemplateProvider` implements `TemplateProvider.render()` using Jinja2 HTML templates + `weasyprint` for PDF conversion. Three styles (modern, bold, classic) rotate deterministically per listing. Factory updated to use this as default when no Canva key is set.

**Tech Stack:** weasyprint, Jinja2 (already installed), Python 3.12

---

## File Structure

```
src/listingjet/providers/
  html_template.py                      # CREATE — HtmlTemplateProvider class
  templates/
    modern.html                         # CREATE — clean white, big hero
    bold.html                           # CREATE — brand colors prominent
    classic.html                        # CREATE — traditional layout
    base.css                            # CREATE — shared print styles
  factory.py                            # MODIFY — add HtmlTemplateProvider fallback
tests/test_providers/
  test_html_template.py                 # CREATE — tests
pyproject.toml                          # MODIFY — add weasyprint dependency
```

---

### Task 1: Install weasyprint

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add weasyprint to dependencies**

In `pyproject.toml`, add `weasyprint` to the dependencies list:

```bash
cd C:/Users/Jeff/launchlens
pip install weasyprint
```

Then add it to `pyproject.toml` dependencies section.

- [ ] **Step 2: Verify weasyprint works**

```bash
cd C:/Users/Jeff/launchlens
python -c "import weasyprint; print('weasyprint', weasyprint.__version__)"
```

Expected: Prints version number without errors.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add pyproject.toml
git commit -m "chore: add weasyprint dependency for HTML-to-PDF flyer generation"
```

---

### Task 2: Create shared base.css

**Files:**
- Create: `src/listingjet/providers/templates/base.css`

- [ ] **Step 1: Create the templates directory**

```bash
mkdir -p C:/Users/Jeff/launchlens/src/listingjet/providers/templates
```

- [ ] **Step 2: Create base.css**

Create `src/listingjet/providers/templates/base.css`:

```css
/* base.css — shared print styles for listing flyers */
@page {
  size: letter portrait;
  margin: 0;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  width: 8.5in;
  height: 11in;
  font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1a1a1a;
  line-height: 1.4;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

.page {
  width: 8.5in;
  height: 11in;
  position: relative;
  overflow: hidden;
}

/* Hero image */
.hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.hero-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  color: white;
  text-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

/* Typography */
.price {
  font-weight: 800;
  letter-spacing: -0.02em;
}

.address {
  font-weight: 600;
}

.specs {
  display: flex;
  gap: 24px;
  font-size: 14px;
  color: #555;
}

.spec-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.spec-value {
  font-weight: 700;
  color: #1a1a1a;
}

.spec-label {
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.05em;
}

/* Brand bar */
.brand-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
}

.brand-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-name {
  font-weight: 700;
  font-size: 14px;
}

.brokerage-name {
  font-size: 12px;
  color: #666;
}

.brand-logo {
  height: 40px;
  width: auto;
  object-fit: contain;
}

/* Utility */
.text-white { color: white; }
.text-center { text-align: center; }
```

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/listingjet/providers/templates/
git commit -m "feat: add base.css shared print styles for flyer templates"
```

---

### Task 3: Create modern.html template

**Files:**
- Create: `src/listingjet/providers/templates/modern.html`

- [ ] **Step 1: Create modern.html**

Create `src/listingjet/providers/templates/modern.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="base.css">
  <style>
    .hero-section {
      height: 4.4in;
      position: relative;
      overflow: hidden;
    }
    .content-section {
      padding: 28px 32px 16px;
    }
    .price {
      font-size: 36px;
      margin-bottom: 4px;
    }
    .address {
      font-size: 18px;
      color: #333;
      margin-bottom: 16px;
    }
    .specs {
      margin-bottom: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid #e5e5e5;
    }
    .spec-value { font-size: 20px; }
    .description {
      font-size: 13px;
      color: #444;
      line-height: 1.6;
      margin-bottom: 20px;
    }
    .accent-line {
      height: 3px;
      width: 60px;
      margin-bottom: 12px;
    }
    .brand-bar {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      background: #fafafa;
      border-top: 1px solid #e5e5e5;
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="hero-section">
      {% if hero_image_url %}
        <img class="hero-img" src="{{ hero_image_url }}" alt="Property">
      {% else %}
        <div class="hero-placeholder" style="background: linear-gradient(135deg, {{ primary_color }}, {{ primary_color }}99);">
          {{ address_line }}
        </div>
      {% endif %}
    </div>

    <div class="content-section">
      <div class="accent-line" style="background: {{ primary_color }};"></div>
      <div class="price">{{ price_formatted }}</div>
      <div class="address">{{ address_line }}</div>

      <div class="specs">
        {% if beds %}<div class="spec-item"><span class="spec-value">{{ beds }}</span><span class="spec-label">Beds</span></div>{% endif %}
        {% if baths %}<div class="spec-item"><span class="spec-value">{{ baths }}</span><span class="spec-label">Baths</span></div>{% endif %}
        {% if sqft_formatted %}<div class="spec-item"><span class="spec-value">{{ sqft_formatted }}</span><span class="spec-label">Sq Ft</span></div>{% endif %}
      </div>

      {% if description %}
        <div class="description">{{ description }}</div>
      {% endif %}
    </div>

    <div class="brand-bar">
      <div class="brand-info">
        {% if agent_name %}<div class="agent-name">{{ agent_name }}</div>{% endif %}
        {% if brokerage_name %}<div class="brokerage-name">{{ brokerage_name }}</div>{% endif %}
      </div>
      {% if logo_url %}
        <img class="brand-logo" src="{{ logo_url }}" alt="Logo">
      {% endif %}
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/listingjet/providers/templates/modern.html
git commit -m "feat: add modern flyer template (clean white, big hero)"
```

---

### Task 4: Create bold.html template

**Files:**
- Create: `src/listingjet/providers/templates/bold.html`

- [ ] **Step 1: Create bold.html**

Create `src/listingjet/providers/templates/bold.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="base.css">
  <style>
    .header-band {
      padding: 28px 32px 20px;
      color: white;
    }
    .header-band .price {
      font-size: 40px;
      color: white;
    }
    .header-band .address {
      font-size: 16px;
      color: rgba(255,255,255,0.9);
      margin-top: 4px;
    }
    .hero-section {
      padding: 20px 32px;
      display: flex;
      justify-content: center;
    }
    .hero-frame {
      width: 85%;
      height: 3.6in;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    }
    .specs-row {
      display: flex;
      justify-content: center;
      gap: 16px;
      padding: 16px 32px;
    }
    .spec-badge {
      padding: 8px 20px;
      border-radius: 8px;
      text-align: center;
      color: white;
      font-weight: 700;
      font-size: 14px;
    }
    .spec-badge .num {
      font-size: 22px;
      display: block;
    }
    .spec-badge .label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      opacity: 0.9;
    }
    .description {
      padding: 8px 40px 16px;
      font-size: 13px;
      color: #444;
      line-height: 1.6;
      text-align: center;
    }
    .footer-band {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 16px 32px;
      color: white;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .footer-band .agent-name { font-weight: 700; font-size: 15px; }
    .footer-band .brokerage-name { font-size: 12px; opacity: 0.85; }
    .footer-band .brand-logo { height: 36px; filter: brightness(0) invert(1); }
  </style>
</head>
<body>
  <div class="page">
    <div class="header-band" style="background: {{ primary_color }};">
      <div class="price">{{ price_formatted }}</div>
      <div class="address">{{ address_line }}</div>
    </div>

    <div class="hero-section">
      <div class="hero-frame">
        {% if hero_image_url %}
          <img class="hero-img" src="{{ hero_image_url }}" alt="Property">
        {% else %}
          <div class="hero-placeholder" style="background: linear-gradient(135deg, #667, #334);">
            {{ address_line }}
          </div>
        {% endif %}
      </div>
    </div>

    <div class="specs-row">
      {% if beds %}
        <div class="spec-badge" style="background: {{ secondary_color or primary_color }};">
          <span class="num">{{ beds }}</span><span class="label">Beds</span>
        </div>
      {% endif %}
      {% if baths %}
        <div class="spec-badge" style="background: {{ secondary_color or primary_color }};">
          <span class="num">{{ baths }}</span><span class="label">Baths</span>
        </div>
      {% endif %}
      {% if sqft_formatted %}
        <div class="spec-badge" style="background: {{ secondary_color or primary_color }};">
          <span class="num">{{ sqft_formatted }}</span><span class="label">Sq Ft</span>
        </div>
      {% endif %}
    </div>

    {% if description %}
      <div class="description">{{ description }}</div>
    {% endif %}

    <div class="footer-band" style="background: {{ primary_color }};">
      <div class="brand-info">
        {% if agent_name %}<div class="agent-name">{{ agent_name }}</div>{% endif %}
        {% if brokerage_name %}<div class="brokerage-name">{{ brokerage_name }}</div>{% endif %}
      </div>
      {% if logo_url %}
        <img class="brand-logo" src="{{ logo_url }}" alt="Logo">
      {% endif %}
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/listingjet/providers/templates/bold.html
git commit -m "feat: add bold flyer template (brand colors prominent)"
```

---

### Task 5: Create classic.html template

**Files:**
- Create: `src/listingjet/providers/templates/classic.html`

- [ ] **Step 1: Create classic.html**

Create `src/listingjet/providers/templates/classic.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="base.css">
  <style>
    .page {
      padding: 24px;
    }
    .frame {
      border: 2px solid #ccc;
      height: calc(11in - 48px);
      display: flex;
      flex-direction: column;
    }
    .top-section {
      display: flex;
      flex: 1;
      min-height: 0;
    }
    .photo-side {
      width: 50%;
      overflow: hidden;
    }
    .details-side {
      width: 50%;
      padding: 28px 24px;
      display: flex;
      flex-direction: column;
    }
    .details-heading {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 4px;
    }
    .details-price {
      font-size: 32px;
      font-weight: 800;
      margin-bottom: 8px;
    }
    .details-address {
      font-size: 15px;
      font-weight: 600;
      color: #333;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid #ddd;
    }
    .detail-row {
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      font-size: 13px;
      border-bottom: 1px solid #f0f0f0;
    }
    .detail-label { color: #666; }
    .detail-value { font-weight: 600; }
    .description {
      margin-top: 16px;
      font-size: 12px;
      color: #555;
      line-height: 1.6;
      flex: 1;
    }
    .classic-brand {
      padding: 14px 24px;
      border-top: 2px solid #ccc;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .classic-brand .agent-name { font-weight: 700; font-size: 14px; }
    .classic-brand .brokerage-name { font-size: 11px; color: #666; }
    .classic-brand .brand-logo { height: 32px; }
  </style>
</head>
<body>
  <div class="page">
    <div class="frame">
      <div class="top-section">
        <div class="photo-side">
          {% if hero_image_url %}
            <img class="hero-img" src="{{ hero_image_url }}" alt="Property">
          {% else %}
            <div class="hero-placeholder" style="background: linear-gradient(135deg, {{ primary_color }}66, {{ primary_color }}33);">
              {{ address_line }}
            </div>
          {% endif %}
        </div>
        <div class="details-side">
          <div class="details-heading" style="color: {{ primary_color }};">For Sale</div>
          <div class="details-price">{{ price_formatted }}</div>
          <div class="details-address">{{ address_line }}</div>

          {% if beds %}
            <div class="detail-row"><span class="detail-label">Bedrooms</span><span class="detail-value">{{ beds }}</span></div>
          {% endif %}
          {% if baths %}
            <div class="detail-row"><span class="detail-label">Bathrooms</span><span class="detail-value">{{ baths }}</span></div>
          {% endif %}
          {% if sqft_formatted %}
            <div class="detail-row"><span class="detail-label">Square Feet</span><span class="detail-value">{{ sqft_formatted }}</span></div>
          {% endif %}

          {% if description %}
            <div class="description">{{ description }}</div>
          {% endif %}
        </div>
      </div>

      <div class="classic-brand">
        <div class="brand-info">
          {% if agent_name %}<div class="agent-name">{{ agent_name }}</div>{% endif %}
          {% if brokerage_name %}<div class="brokerage-name">{{ brokerage_name }}</div>{% endif %}
        </div>
        {% if logo_url %}
          <img class="brand-logo" src="{{ logo_url }}" alt="Logo">
        {% endif %}
      </div>
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/listingjet/providers/templates/classic.html
git commit -m "feat: add classic flyer template (traditional side-by-side layout)"
```

---

### Task 6: Create HtmlTemplateProvider

**Files:**
- Create: `src/listingjet/providers/html_template.py`
- Test: `tests/test_providers/test_html_template.py`

- [ ] **Step 1: Write the tests**

Create `tests/test_providers/test_html_template.py`:

```python
import pytest

from listingjet.providers.html_template import HtmlTemplateProvider


@pytest.fixture
def provider():
    return HtmlTemplateProvider()


@pytest.fixture
def sample_data():
    return {
        "listing_id": "abc-123",
        "address": {"street": "123 Main St", "city": "Austin", "state": "TX", "zip": "78701"},
        "metadata": {"beds": 3, "baths": 2, "sqft": 1800, "price": 425000},
        "hero_image_url": None,
        "hero_asset_id": None,
        "primary_color": "#2563EB",
        "secondary_color": "#10B981",
        "agent_name": "Jane Smith",
        "brokerage_name": "Premier Realty",
        "logo_url": None,
        "font": None,
        "description": "Beautiful home in downtown Austin.",
    }


@pytest.mark.asyncio
async def test_render_modern(provider, sample_data):
    result = await provider.render("modern", sample_data)
    assert isinstance(result, bytes)
    assert result[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_render_bold(provider, sample_data):
    result = await provider.render("bold", sample_data)
    assert isinstance(result, bytes)
    assert result[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_render_classic(provider, sample_data):
    result = await provider.render("classic", sample_data)
    assert isinstance(result, bytes)
    assert result[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_auto_is_deterministic(provider, sample_data):
    result1 = await provider.render("auto", sample_data)
    result2 = await provider.render("auto", sample_data)
    # Same listing_id should produce same template choice, hence same PDF size (roughly)
    assert abs(len(result1) - len(result2)) < 100


@pytest.mark.asyncio
async def test_auto_varies_by_listing_id(provider, sample_data):
    styles_used = set()
    for i in range(20):
        data = {**sample_data, "listing_id": f"listing-{i}"}
        # Check which style is selected by the provider
        style = provider._select_style("auto", data)
        styles_used.add(style)
    # With 20 different listing IDs, we should hit at least 2 of the 3 styles
    assert len(styles_used) >= 2


@pytest.mark.asyncio
async def test_missing_hero_uses_placeholder(provider, sample_data):
    sample_data["hero_image_url"] = None
    result = await provider.render("modern", sample_data)
    assert isinstance(result, bytes)
    assert result[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_missing_optional_fields(provider):
    minimal_data = {
        "listing_id": "min-123",
        "address": {"street": "456 Oak Ave"},
        "metadata": {"price": 300000},
        "hero_image_url": None,
        "hero_asset_id": None,
        "primary_color": "#FF0000",
        "secondary_color": None,
        "agent_name": None,
        "brokerage_name": None,
        "logo_url": None,
        "font": None,
    }
    result = await provider.render("modern", minimal_data)
    assert isinstance(result, bytes)
    assert result[:5] == b"%PDF-"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/Jeff/launchlens
python -m pytest tests/test_providers/test_html_template.py -v 2>&1 | head -20
```

Expected: ImportError — `html_template` module doesn't exist yet.

- [ ] **Step 3: Create HtmlTemplateProvider**

Create `src/listingjet/providers/html_template.py`:

```python
"""Self-hosted HTML-to-PDF flyer generator. No external API needed."""
import hashlib
from pathlib import Path

import weasyprint
from jinja2 import Environment, FileSystemLoader

from .base import TemplateProvider

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_STYLES = ["modern", "bold", "classic"]

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


class HtmlTemplateProvider(TemplateProvider):
    """Renders listing flyers as PDF from HTML/CSS templates."""

    async def render(self, template_id: str, data: dict) -> bytes:
        style = self._select_style(template_id, data)
        template = _jinja_env.get_template(f"{style}.html")
        context = self._build_context(data)
        html = template.render(**context)
        pdf_bytes = weasyprint.HTML(
            string=html,
            base_url=str(_TEMPLATE_DIR),
        ).write_pdf()
        return pdf_bytes

    def _select_style(self, template_id: str, data: dict) -> str:
        if template_id in _STYLES:
            return template_id
        # "auto" or unrecognized: deterministic pick based on listing_id
        listing_id = data.get("listing_id", "default")
        idx = int(hashlib.md5(listing_id.encode()).hexdigest(), 16) % len(_STYLES)
        return _STYLES[idx]

    @staticmethod
    def _build_context(data: dict) -> dict:
        address = data.get("address", {})
        metadata = data.get("metadata", {})

        parts = [address.get("street", "")]
        city_state = ", ".join(filter(None, [address.get("city"), address.get("state")]))
        if city_state:
            parts.append(city_state)
        if address.get("zip"):
            parts.append(address["zip"])
        address_line = " ".join(filter(None, parts))

        price = metadata.get("price")
        if isinstance(price, (int, float)) and price:
            price_formatted = f"${price:,.0f}"
        elif price:
            price_formatted = str(price)
        else:
            price_formatted = ""

        sqft = metadata.get("sqft")
        if isinstance(sqft, (int, float)) and sqft:
            sqft_formatted = f"{sqft:,}"
        else:
            sqft_formatted = ""

        return {
            "address_line": address_line,
            "price_formatted": price_formatted,
            "beds": metadata.get("beds"),
            "baths": metadata.get("baths"),
            "sqft_formatted": sqft_formatted,
            "description": data.get("description", ""),
            "hero_image_url": data.get("hero_image_url"),
            "primary_color": data.get("primary_color", "#2563EB"),
            "secondary_color": data.get("secondary_color"),
            "agent_name": data.get("agent_name"),
            "brokerage_name": data.get("brokerage_name"),
            "logo_url": data.get("logo_url"),
        }
```

- [ ] **Step 4: Run tests**

```bash
cd C:/Users/Jeff/launchlens
python -m pytest tests/test_providers/test_html_template.py -v
```

Expected: All 7 tests pass.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/listingjet/providers/html_template.py tests/test_providers/test_html_template.py
git commit -m "feat: add HtmlTemplateProvider with 3 rotating flyer styles"
```

---

### Task 7: Update factory to use HtmlTemplateProvider as default

**Files:**
- Modify: `src/listingjet/providers/factory.py:29-37`
- Test: `tests/test_providers/test_factory_real.py`

- [ ] **Step 1: Read the current factory.py**

```bash
cat C:/Users/Jeff/launchlens/src/listingjet/providers/factory.py
```

- [ ] **Step 2: Update get_template_provider()**

In `src/listingjet/providers/factory.py`, replace the `get_template_provider` function:

```python
def get_template_provider() -> TemplateProvider:
    if settings.use_mock_providers:
        from .mock import MockTemplateProvider
        return MockTemplateProvider()
    if settings.canva_api_key:
        from .canva import CanvaTemplateProvider
        return CanvaTemplateProvider(api_key=settings.canva_api_key, llm_provider=get_llm_provider())
    from .html_template import HtmlTemplateProvider
    return HtmlTemplateProvider()
```

- [ ] **Step 3: Run existing factory tests**

```bash
cd C:/Users/Jeff/launchlens
python -m pytest tests/test_providers/test_factory_real.py -v
```

Expected: Existing tests still pass (they test mock_providers=True and canva_api_key scenarios).

- [ ] **Step 4: Run the full test suite**

```bash
cd C:/Users/Jeff/launchlens
python -m pytest tests/ -x -q --tb=short 2>&1 | tail -15
```

Expected: No new failures.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/listingjet/providers/factory.py
git commit -m "feat: use HtmlTemplateProvider as default when no Canva key configured"
```

---

## Summary of Commands

| Action | Command |
|--------|---------|
| Install weasyprint | `pip install weasyprint` |
| Run flyer tests | `python -m pytest tests/test_providers/test_html_template.py -v` |
| Run all tests | `python -m pytest tests/ -x -q --tb=short` |
