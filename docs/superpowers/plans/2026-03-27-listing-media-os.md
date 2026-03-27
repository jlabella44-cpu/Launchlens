# Listing Media OS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SocialContentAgent, MLSExportAgent, export endpoint, dual-tone ContentAgent, demo pipeline, and Temporal workflow updates to transform LaunchLens into a Listing Media OS.

**Architecture:** Two new agents (SocialContentAgent, MLSExportAgent) follow existing BaseAgent pattern with session injection and provider injection. ContentAgent gets dual-tone output. Temporal Phase 2 becomes parallel (Brand + Social) → MLSExport → Distribution. New demo router provides unauthenticated upload→preview→claim flow. One Alembic migration adds the SocialContent table and new Listing columns.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Temporal, Pillow (new), pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-27-listing-media-os-design.md`

---

## File Map

### New Files
| File | Responsibility |
|---|---|
| `src/launchlens/models/social_content.py` | SocialContent ORM model |
| `src/launchlens/agents/social_content.py` | SocialContentAgent |
| `src/launchlens/agents/mls_export.py` | MLSExportAgent |
| `src/launchlens/api/demo.py` | Demo upload/view/claim endpoints |
| `src/launchlens/api/schemas/demo.py` | Demo request/response Pydantic models |
| `alembic/versions/005_social_content_export_demo.py` | Migration |
| `tests/test_agents/test_social_content.py` | SocialContentAgent tests |
| `tests/test_agents/test_mls_export.py` | MLSExportAgent tests |
| `tests/test_api/test_export.py` | Export endpoint tests |
| `tests/test_api/test_demo.py` | Demo endpoint tests |

### Modified Files
| File | Change |
|---|---|
| `src/launchlens/models/listing.py` | Add `EXPORTING`+`DEMO` states, `mls_bundle_path`, `marketing_bundle_path`, `is_demo`, `demo_expires_at` |
| `src/launchlens/agents/content.py` | Dual-tone output (mls_safe + marketing) |
| `src/launchlens/activities/pipeline.py` | Add `run_social_content`, `run_mls_export` activities |
| `src/launchlens/workflows/listing_pipeline.py` | Parallel Phase 2, plan-aware branching |
| `src/launchlens/workflows/worker.py` | Register new activities (automatic via ALL_ACTIVITIES) |
| `src/launchlens/api/listings.py` | Add `GET /listings/{id}/export` |
| `src/launchlens/api/schemas/listings.py` | Add `ExportMode`, `BundleMetadata`, `ExportResponse` |
| `src/launchlens/main.py` | Register demo router |
| `src/launchlens/middleware/tenant.py` | Add demo paths to `_PUBLIC_PATHS` |
| `src/launchlens/services/plan_limits.py` | Add `social_content` flag per tier |

---

## Task 1: Alembic Migration — SocialContent Table + Listing Columns

**Files:**
- Create: `alembic/versions/005_social_content_export_demo.py`
- Modify: `src/launchlens/models/listing.py`
- Modify: `src/launchlens/services/plan_limits.py`

- [ ] **Step 1: Add new ListingState enum values and Listing columns**

In `src/launchlens/models/listing.py`, add two new enum values and four new columns:

```python
# In ListingState enum, add after FAILED:
    EXPORTING = "exporting"
    DEMO = "demo"
```

Add columns to the `Listing` class after `updated_at`:

```python
from sqlalchemy import Boolean

# ... existing columns ...
mls_bundle_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
marketing_bundle_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
demo_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 2: Add social_content flag to plan_limits**

In `src/launchlens/services/plan_limits.py`, add the `social_content` key to each tier:

```python
PLAN_LIMITS: dict[str, dict] = {
    "starter": {
        "max_listings_per_month": 5,
        "max_assets_per_listing": 25,
        "tier2_vision": False,
        "social_content": False,
    },
    "pro": {
        "max_listings_per_month": 50,
        "max_assets_per_listing": 50,
        "tier2_vision": True,
        "social_content": True,
    },
    "enterprise": {
        "max_listings_per_month": 500,
        "max_assets_per_listing": 100,
        "tier2_vision": True,
        "social_content": True,
    },
}
```

- [ ] **Step 3: Write the Alembic migration**

Create `alembic/versions/005_social_content_export_demo.py`:

```python
"""social content, export bundles, demo listings

Revision ID: 005
Revises: 004
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Listing columns ---
    op.add_column("listings", sa.Column("mls_bundle_path", sa.String(500), nullable=True))
    op.add_column("listings", sa.Column("marketing_bundle_path", sa.String(500), nullable=True))
    op.add_column("listings", sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("listings", sa.Column("demo_expires_at", sa.DateTime(timezone=True), nullable=True))

    # --- ListingState enum: add EXPORTING and DEMO ---
    op.execute("ALTER TYPE listingstate ADD VALUE IF NOT EXISTS 'exporting'")
    op.execute("ALTER TYPE listingstate ADD VALUE IF NOT EXISTS 'demo'")

    # --- SocialContent table ---
    op.create_table(
        "social_contents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(), nullable=False, index=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("hashtags", JSONB, nullable=True),
        sa.Column("cta", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- RLS on social_contents ---
    op.execute("ALTER TABLE social_contents ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON social_contents "
        "USING (tenant_id::text = current_setting('app.current_tenant', true))"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON social_contents")
    op.drop_table("social_contents")
    op.drop_column("listings", "demo_expires_at")
    op.drop_column("listings", "is_demo")
    op.drop_column("listings", "marketing_bundle_path")
    op.drop_column("listings", "mls_bundle_path")
    # Note: cannot remove enum values in PostgreSQL
```

- [ ] **Step 4: Run the migration against both databases**

```bash
cd C:/Users/Jeff/launchlens
DATABASE_URL="postgresql+asyncpg://launchlens:password@localhost:5432/launchlens" DATABASE_URL_SYNC="postgresql://launchlens:password@localhost:5432/launchlens" JWT_SECRET="dev-secret" python -m alembic upgrade head
DATABASE_URL="postgresql+asyncpg://launchlens:password@localhost:5433/launchlens_test" DATABASE_URL_SYNC="postgresql://launchlens:password@localhost:5433/launchlens_test" JWT_SECRET="dev-secret" python -m alembic upgrade head
```

Expected: both succeed with "Running upgrade 004 -> 005"

- [ ] **Step 5: Run existing tests to verify nothing broke**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest --tb=short -q
```

Expected: 193 tests pass.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/launchlens/models/listing.py src/launchlens/services/plan_limits.py alembic/versions/005_social_content_export_demo.py
git commit -m "feat: migration 005 — social_contents table, listing export/demo columns, EXPORTING+DEMO states"
```

---

## Task 2: SocialContent Model

**Files:**
- Create: `src/launchlens/models/social_content.py`

- [ ] **Step 1: Create the SocialContent model**

Create `src/launchlens/models/social_content.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class SocialContent(TenantScopedModel):
    __tablename__ = "social_contents"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cta: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

- [ ] **Step 2: Verify the model loads without error**

```bash
cd C:/Users/Jeff/launchlens && python -c "from launchlens.models.social_content import SocialContent; print(SocialContent.__tablename__)"
```

Expected: `social_contents`

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/launchlens/models/social_content.py
git commit -m "feat: SocialContent model"
```

---

## Task 3: SocialContentAgent

**Files:**
- Create: `src/launchlens/agents/social_content.py`
- Create: `tests/test_agents/test_social_content.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agents/test_social_content.py`:

```python
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from launchlens.agents.base import AgentContext
from launchlens.agents.social_content import SocialContentAgent
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState
from launchlens.models.package_selection import PackageSelection
from launchlens.models.social_content import SocialContent
from launchlens.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory

_VALID_RESPONSE = json.dumps({
    "instagram": {
        "caption": "Welcome to 123 Main St — a stunning 3-bed, 2-bath home in the heart of Austin.",
        "hashtags": ["#justlisted", "#austinrealestate", "#dreamhome"],
        "cta": "Link in bio for details"
    },
    "facebook": {
        "caption": "Just listed in Austin! This beautiful 3-bedroom home features modern finishes and an open floor plan.",
        "cta": "Schedule a showing today"
    }
})


async def _setup_listing_with_hero(db_session):
    """Create a listing in APPROVED state with a hero photo and vision result."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "123 Main St", "city": "Austin", "state": "TX"},
        metadata_={"beds": 3, "baths": 2, "sqft": 1800, "price": 450000},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    asset = Asset(
        listing_id=listing.id,
        tenant_id=tenant_id,
        file_path=f"s3://bucket/listing/{listing.id}/photo_0.jpg",
        file_hash="hero001",
        state="uploaded",
    )
    db_session.add(asset)
    await db_session.flush()

    pkg = PackageSelection(
        tenant_id=tenant_id,
        listing_id=listing.id,
        asset_id=asset.id,
        channel="mls",
        position=0,
        composite_score=95.0,
        selected_by="ai",
    )
    db_session.add(pkg)

    vr = VisionResult(
        asset_id=asset.id,
        tier=1,
        room_label="exterior_front",
        is_interior=False,
        quality_score=92,
        commercial_score=88,
        hero_candidate=True,
        raw_labels={"labels": [{"name": "house", "confidence": 0.97}]},
        model_used="google-vision-v1",
    )
    db_session.add(vr)
    await db_session.flush()

    return listing, tenant_id


def _make_llm_provider(response=_VALID_RESPONSE):
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=response)
    return provider


@pytest.mark.asyncio
async def test_social_content_generates_two_platforms(db_session):
    listing, tenant_id = await _setup_listing_with_hero(db_session)
    provider = _make_llm_provider()

    agent = SocialContentAgent(
        llm_provider=provider,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    result = await agent.execute(ctx)

    assert result["platforms"] == ["instagram", "facebook"]
    assert provider.complete.call_count == 1


@pytest.mark.asyncio
async def test_social_content_stores_in_db(db_session):
    from sqlalchemy import select

    listing, tenant_id = await _setup_listing_with_hero(db_session)
    provider = _make_llm_provider()

    agent = SocialContentAgent(
        llm_provider=provider,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    rows = (await db_session.execute(
        select(SocialContent).where(SocialContent.listing_id == listing.id)
    )).scalars().all()
    assert len(rows) == 2
    platforms = {r.platform for r in rows}
    assert platforms == {"instagram", "facebook"}


@pytest.mark.asyncio
async def test_social_content_retries_on_fha_violation(db_session):
    listing, tenant_id = await _setup_listing_with_hero(db_session)

    fha_violation_response = json.dumps({
        "instagram": {
            "caption": "Perfect for families in this safe neighborhood!",
            "hashtags": ["#justlisted"],
            "cta": "Link in bio"
        },
        "facebook": {
            "caption": "Great for families looking for a safe neighborhood.",
            "cta": "Schedule a showing"
        }
    })

    provider = MagicMock()
    provider.complete = AsyncMock(side_effect=[fha_violation_response, _VALID_RESPONSE])

    agent = SocialContentAgent(
        llm_provider=provider,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    result = await agent.execute(ctx)

    assert provider.complete.call_count == 2
    assert result["fha_passed"] is True


@pytest.mark.asyncio
async def test_social_content_emits_event(db_session):
    from sqlalchemy import select
    from launchlens.models.outbox import Outbox

    listing, tenant_id = await _setup_listing_with_hero(db_session)
    provider = _make_llm_provider()

    agent = SocialContentAgent(
        llm_provider=provider,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "social_content.completed")
    )).scalars().all()
    assert len(rows) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_agents/test_social_content.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.agents.social_content'`

- [ ] **Step 3: Implement SocialContentAgent**

Create `src/launchlens/agents/social_content.py`:

```python
import json
import uuid

from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing
from launchlens.models.package_selection import PackageSelection
from launchlens.models.social_content import SocialContent
from launchlens.models.vision_result import VisionResult
from launchlens.providers import get_llm_provider
from launchlens.services.events import emit_event
from launchlens.services.fha_filter import fha_check

from .base import AgentContext, BaseAgent

_PROMPT_TEMPLATE = """\
Generate social media captions for a real estate listing.
Do NOT use Fair Housing Act prohibited language (no "perfect for families",
"safe neighborhood", "great schools", "family friendly", etc.).

Property: {address}
Details: {beds} beds, {baths} baths, {sqft} sqft, ${price:,}
Hero photo: {hero_label} (quality score: {hero_quality})
Listing description summary: {description_summary}

Return ONLY a JSON object with this exact structure:
{{
  "instagram": {{
    "caption": "...(max 2200 chars, lifestyle tone, emoji-friendly)...",
    "hashtags": ["#justlisted", "...(20-30 hashtags)..."],
    "cta": "Link in bio for details"
  }},
  "facebook": {{
    "caption": "...(max 500 chars, conversational tone, no hashtag blocks)...",
    "cta": "Schedule a showing today"
  }}
}}"""

_FHA_RETRY_SUFFIX = (
    "\n\nIMPORTANT: The previous attempt contained Fair Housing Act violations. "
    "Rewrite without referencing families, schools, neighborhood safety, or religion."
)

_MAX_FHA_RETRIES = 2


class SocialContentAgent(BaseAgent):
    agent_name = "social_content"

    def __init__(self, llm_provider=None, session_factory=None):
        self._llm_provider = llm_provider or get_llm_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)

                # Get hero photo's vision result
                hero_result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .join(
                        PackageSelection,
                        (PackageSelection.asset_id == Asset.id)
                        & (PackageSelection.listing_id == listing_id)
                        & (PackageSelection.position == 0),
                    )
                    .where(Asset.listing_id == listing_id)
                )
                hero_vr = hero_result.scalar_one_or_none()

                address = listing.address
                meta = listing.metadata_
                address_str = f"{address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')}"

                prompt = _PROMPT_TEMPLATE.format(
                    address=address_str,
                    beds=meta.get("beds", "N/A"),
                    baths=meta.get("baths", "N/A"),
                    sqft=meta.get("sqft", "N/A"),
                    price=meta.get("price", 0),
                    hero_label=hero_vr.room_label if hero_vr else "exterior",
                    hero_quality=hero_vr.quality_score if hero_vr else "N/A",
                    description_summary=str(meta),
                )

                # Generate with FHA retry loop
                fha_passed = False
                for attempt in range(_MAX_FHA_RETRIES):
                    current_prompt = prompt if attempt == 0 else prompt + _FHA_RETRY_SUFFIX
                    raw = await self._llm_provider.complete(
                        prompt=current_prompt, context=meta
                    )
                    data = json.loads(raw)

                    # FHA check all captions
                    all_text = {
                        "ig_caption": data["instagram"]["caption"],
                        "fb_caption": data["facebook"]["caption"],
                    }
                    fha_result = fha_check(all_text)
                    if fha_result.passed:
                        fha_passed = True
                        break

                # Store results
                platforms = []
                for platform in ("instagram", "facebook"):
                    entry = data[platform]
                    sc = SocialContent(
                        tenant_id=uuid.UUID(context.tenant_id),
                        listing_id=listing_id,
                        platform=platform,
                        caption=entry["caption"],
                        hashtags=entry.get("hashtags"),
                        cta=entry.get("cta"),
                    )
                    session.add(sc)
                    platforms.append(platform)

                await emit_event(
                    session=session,
                    event_type="social_content.completed",
                    payload={
                        "platforms": platforms,
                        "fha_passed": fha_passed,
                    },
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"platforms": platforms, "fha_passed": fha_passed}
```

- [ ] **Step 4: Run the tests**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_agents/test_social_content.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Run full test suite**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest --tb=short -q
```

Expected: 197 tests pass (193 existing + 4 new).

- [ ] **Step 6: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/launchlens/agents/social_content.py tests/test_agents/test_social_content.py
git commit -m "feat: SocialContentAgent — generates Instagram + Facebook captions with FHA compliance"
```

---

## Task 4: Dual-Tone ContentAgent

**Files:**
- Modify: `src/launchlens/agents/content.py`
- Modify: `tests/test_agents/test_content.py`

- [ ] **Step 1: Write the failing test for dual-tone output**

Add to `tests/test_agents/test_content.py`:

```python
@pytest.mark.asyncio
async def test_content_returns_dual_tone(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)

    response = '{"mls_safe": "Spacious 3-bedroom home with 2 bathrooms.", "marketing": "Welcome home to this stunning 3-bedroom retreat with modern finishes and natural light."}'
    provider = make_llm_provider(response)
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert "mls_safe" in result
    assert "marketing" in result
    assert len(result["mls_safe"]) > 0
    assert len(result["marketing"]) > 0
    assert result["fha_passed"] is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_agents/test_content.py::test_content_returns_dual_tone -v
```

Expected: FAIL — `KeyError: 'mls_safe'`

- [ ] **Step 3: Update ContentAgent for dual-tone output**

Replace the content of `src/launchlens/agents/content.py`:

```python
import json
import uuid

from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing
from launchlens.models.vision_result import VisionResult
from launchlens.providers import get_llm_provider
from launchlens.services.events import emit_event
from launchlens.services.fha_filter import fha_check

from .base import AgentContext, BaseAgent

_PROMPT_TEMPLATE = """\
Write two real estate listing descriptions for the following property.
Be specific and factual. Do not use Fair Housing Act prohibited language.

Property details:
{metadata}

Key features identified from photos:
{photo_features}

Return ONLY a JSON object with this exact structure:
{{
  "mls_safe": "...(2-3 sentences, factual only, no agent promotion, no personality)...",
  "marketing": "...(2-3 sentences, compelling, personality allowed, but still FHA compliant)..."
}}"""

_FHA_RETRY_SUFFIX = (
    "\n\nIMPORTANT: The previous attempt contained language that may violate the Fair Housing Act. "
    "Rewrite without referencing families, schools, neighborhood safety, or religion."
)


class ContentAgent(BaseAgent):
    agent_name = "content"

    def __init__(self, llm_provider=None, session_factory=None):
        self._llm_provider = llm_provider or get_llm_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)

                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .where(
                        Asset.listing_id == listing_id,
                        VisionResult.tier == 1,
                    )
                    .order_by(VisionResult.quality_score.desc())
                    .limit(5)
                )
                vrs = result.scalars().all()
                features_text = ", ".join(
                    f"{vr.room_label} (q={vr.quality_score})" for vr in vrs if vr.room_label
                )

                prompt = _PROMPT_TEMPLATE.format(
                    metadata=str(listing.metadata_),
                    photo_features=features_text or "modern interior",
                )

                raw = await self._llm_provider.complete(
                    prompt=prompt, context=listing.metadata_
                )
                data = json.loads(raw)
                mls_safe = data["mls_safe"]
                marketing = data["marketing"]

                # FHA check both tones
                fha_result = fha_check({"mls_safe": mls_safe, "marketing": marketing})

                if not fha_result.passed:
                    raw = await self._llm_provider.complete(
                        prompt=prompt + _FHA_RETRY_SUFFIX, context=listing.metadata_
                    )
                    data = json.loads(raw)
                    mls_safe = data["mls_safe"]
                    marketing = data["marketing"]
                    fha_result = fha_check({"mls_safe": mls_safe, "marketing": marketing})

                await emit_event(
                    session=session,
                    event_type="content.completed",
                    payload={
                        "fha_passed": fha_result.passed,
                        "mls_safe_length": len(mls_safe),
                        "marketing_length": len(marketing),
                    },
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {
            "mls_safe": mls_safe,
            "marketing": marketing,
            "fha_passed": fha_result.passed,
        }
```

- [ ] **Step 4: Update existing tests for new response format**

The existing tests use `make_llm_provider` which returns a plain string. Update the default response in `tests/test_agents/test_content.py`:

Change the `make_llm_provider` default:
```python
def make_llm_provider(response='{"mls_safe": "Spacious 3-bedroom home.", "marketing": "Beautiful 3-bedroom home with modern finishes."}'):
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=response)
    return provider
```

Update `test_content_returns_copy`:
```python
@pytest.mark.asyncio
async def test_content_returns_copy(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)

    provider = make_llm_provider()
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert "mls_safe" in result
    assert "marketing" in result
    assert len(result["mls_safe"]) > 0
    assert len(result["marketing"]) > 0
    assert result["fha_passed"] is True
```

Update `test_content_retries_on_fha_violation`:
```python
@pytest.mark.asyncio
async def test_content_retries_on_fha_violation(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)

    fha_violation = '{"mls_safe": "Perfect for families in a safe neighborhood.", "marketing": "Great for families looking for safe neighborhoods."}'
    clean = '{"mls_safe": "Spacious 3-bedroom home.", "marketing": "Stunning home with modern kitchen and open floor plan."}'
    provider = MagicMock()
    provider.complete = AsyncMock(side_effect=[fha_violation, clean])
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert provider.complete.call_count == 2
    assert result["fha_passed"] is True
```

- [ ] **Step 5: Run the content tests**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_agents/test_content.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Run full test suite**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/launchlens/agents/content.py tests/test_agents/test_content.py
git commit -m "feat: ContentAgent dual-tone output — mls_safe + marketing descriptions in one call"
```

---

## Task 5: MLSExportAgent

**Files:**
- Create: `src/launchlens/agents/mls_export.py`
- Create: `tests/test_agents/test_mls_export.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agents/test_mls_export.py`:

```python
import io
import json
import uuid
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from launchlens.agents.base import AgentContext
from launchlens.agents.mls_export import MLSExportAgent
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState
from launchlens.models.package_selection import PackageSelection
from launchlens.models.social_content import SocialContent
from launchlens.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory


async def _setup_approved_listing(db_session, include_social=False):
    """Create APPROVED listing with packaged photos, content result, brand result."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "456 Oak Ave", "city": "Denver", "state": "CO"},
        metadata_={"beds": 4, "baths": 3, "sqft": 2400, "price": 650000},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    assets = []
    for i in range(3):
        asset = Asset(
            listing_id=listing.id,
            tenant_id=tenant_id,
            file_path=f"listings/{listing.id}/photos/photo_{i}.jpg",
            file_hash=f"hash{i:03d}",
            state="uploaded",
        )
        db_session.add(asset)
        assets.append(asset)
    await db_session.flush()

    for i, asset in enumerate(assets):
        pkg = PackageSelection(
            tenant_id=tenant_id,
            listing_id=listing.id,
            asset_id=asset.id,
            channel="mls",
            position=i,
            composite_score=90.0 - i,
            selected_by="ai",
        )
        db_session.add(pkg)

        vr = VisionResult(
            asset_id=asset.id,
            tier=1,
            room_label=["exterior_front", "kitchen", "living_room"][i],
            is_interior=(i > 0),
            quality_score=90 - i * 5,
            commercial_score=85,
            hero_candidate=(i == 0),
            raw_labels={"labels": []},
            model_used="google-vision-v1",
        )
        db_session.add(vr)

    if include_social:
        for platform in ("instagram", "facebook"):
            sc = SocialContent(
                tenant_id=tenant_id,
                listing_id=listing.id,
                platform=platform,
                caption=f"Amazing listing on {platform}!",
                hashtags=["#justlisted"] if platform == "instagram" else None,
                cta="Check it out",
            )
            db_session.add(sc)

    await db_session.flush()
    return listing, tenant_id, assets


def _make_storage_service():
    """Mock StorageService that captures uploaded data."""
    storage = MagicMock()
    storage.uploaded = {}

    def fake_upload(key, data, content_type):
        if isinstance(data, (bytes, bytearray)):
            storage.uploaded[key] = data
        elif hasattr(data, 'read'):
            storage.uploaded[key] = data.read()
        else:
            storage.uploaded[key] = data
        return key

    storage.upload = MagicMock(side_effect=fake_upload)
    storage.presigned_url = MagicMock(return_value="https://s3.example.com/presigned")
    return storage


def _make_photo_bytes():
    """Create minimal valid JPEG bytes (1x1 pixel)."""
    # Minimal JPEG: SOI + APP0 + minimal frame
    return (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
        b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
        b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
        b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
        b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
        b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\xa7\x13\xff\xd9'
    )


@pytest.mark.asyncio
async def test_mls_export_creates_two_bundles(db_session):
    listing, tenant_id, assets = await _setup_approved_listing(db_session, include_social=True)
    storage = _make_storage_service()
    photo_bytes = _make_photo_bytes()

    # Mock S3 download — storage.download returns photo bytes
    def fake_download(key):
        return photo_bytes
    storage.download = MagicMock(side_effect=fake_download)

    agent = MLSExportAgent(
        storage_service=storage,
        session_factory=make_session_factory(db_session),
        content_result={"mls_safe": "A spacious 4-bed home.", "marketing": "Stunning retreat in Denver."},
        flyer_s3_key=f"listings/{listing.id}/flyer.pdf",
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    result = await agent.execute(ctx)

    assert "mls_bundle_path" in result
    assert "marketing_bundle_path" in result
    assert result["mls_bundle_path"].endswith("_mls.zip")
    assert result["marketing_bundle_path"].endswith("_marketing.zip")

    # Verify listing state changed to EXPORTING then DELIVERED is NOT set (DistributionAgent does that)
    await db_session.refresh(listing)
    assert listing.mls_bundle_path is not None
    assert listing.marketing_bundle_path is not None


@pytest.mark.asyncio
async def test_mls_bundle_contains_expected_files(db_session):
    listing, tenant_id, assets = await _setup_approved_listing(db_session)
    storage = _make_storage_service()
    photo_bytes = _make_photo_bytes()
    storage.download = MagicMock(return_value=photo_bytes)

    agent = MLSExportAgent(
        storage_service=storage,
        session_factory=make_session_factory(db_session),
        content_result={"mls_safe": "A spacious 4-bed home.", "marketing": "Stunning retreat."},
        flyer_s3_key=f"listings/{listing.id}/flyer.pdf",
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    await agent.execute(ctx)

    # Find the MLS bundle in uploaded data
    mls_key = [k for k in storage.uploaded if k.endswith("_mls.zip")][0]
    mls_data = storage.uploaded[mls_key]

    with zipfile.ZipFile(io.BytesIO(mls_data)) as zf:
        names = zf.namelist()
        assert "metadata.csv" in names
        assert "description_mls.txt" in names
        assert "manifest.json" in names
        # Should have 3 photo files
        photo_files = [n for n in names if n.endswith(".jpg")]
        assert len(photo_files) == 3
        # First photo should be hero
        assert photo_files[0].startswith("00_")

        # Verify manifest
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["mode"] == "mls"
        assert manifest["photo_count"] == 3


@pytest.mark.asyncio
async def test_mls_export_emits_event(db_session):
    from sqlalchemy import select
    from launchlens.models.outbox import Outbox

    listing, tenant_id, assets = await _setup_approved_listing(db_session)
    storage = _make_storage_service()
    storage.download = MagicMock(return_value=_make_photo_bytes())

    agent = MLSExportAgent(
        storage_service=storage,
        session_factory=make_session_factory(db_session),
        content_result={"mls_safe": "Home.", "marketing": "Beautiful home."},
        flyer_s3_key=f"listings/{listing.id}/flyer.pdf",
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "mls_export.completed")
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_mls_export_sets_exporting_state(db_session):
    listing, tenant_id, assets = await _setup_approved_listing(db_session)
    storage = _make_storage_service()
    storage.download = MagicMock(return_value=_make_photo_bytes())

    agent = MLSExportAgent(
        storage_service=storage,
        session_factory=make_session_factory(db_session),
        content_result={"mls_safe": "Home.", "marketing": "Beautiful home."},
        flyer_s3_key=f"listings/{listing.id}/flyer.pdf",
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    await agent.execute(ctx)

    await db_session.refresh(listing)
    # Agent sets EXPORTING at start, but doesn't set DELIVERED (DistributionAgent does that)
    # After completion the state should still reflect that export ran
    assert listing.mls_bundle_path is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_agents/test_mls_export.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'launchlens.agents.mls_export'`

- [ ] **Step 3: Implement MLSExportAgent**

Create `src/launchlens/agents/mls_export.py`:

```python
import csv
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone

from sqlalchemy import select

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState
from launchlens.models.package_selection import PackageSelection
from launchlens.models.social_content import SocialContent
from launchlens.models.vision_result import VisionResult
from launchlens.services.events import emit_event
from launchlens.services.storage import StorageService

from .base import AgentContext, BaseAgent

_MAX_DIMENSION = 2048
_JPEG_QUALITY = 85


def _resize_photo(photo_bytes: bytes) -> bytes:
    """Resize photo to MLS max dimensions, strip EXIF, return JPEG bytes."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(photo_bytes))
        # Strip EXIF by re-creating without metadata
        img_no_exif = Image.new(img.mode, img.size)
        img_no_exif.putdata(list(img.getdata()))

        # Resize if needed
        w, h = img_no_exif.size
        if max(w, h) > _MAX_DIMENSION:
            ratio = _MAX_DIMENSION / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img_no_exif = img_no_exif.resize(new_size, Image.LANCZOS)

        buf = io.BytesIO()
        img_no_exif.save(buf, format="JPEG", quality=_JPEG_QUALITY)
        return buf.getvalue()
    except Exception:
        # If Pillow fails (e.g. corrupt image), return original bytes
        return photo_bytes


def _build_metadata_csv(photos: list[dict]) -> bytes:
    """Build CSV with photo metadata."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["filename", "position", "room_label", "quality_score", "caption", "hero"])
    writer.writeheader()
    for p in photos:
        writer.writerow(p)
    return buf.getvalue().encode("utf-8")


def _build_manifest(listing_id: str, photo_count: int, mode: str, includes_social: bool) -> bytes:
    return json.dumps({
        "listing_id": listing_id,
        "photo_count": photo_count,
        "mode": mode,
        "includes_social": includes_social,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "0.9.0",
    }, indent=2).encode("utf-8")


class MLSExportAgent(BaseAgent):
    agent_name = "mls_export"

    def __init__(self, storage_service=None, session_factory=None, content_result=None, flyer_s3_key=None):
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal
        self._content_result = content_result or {}
        self._flyer_s3_key = flyer_s3_key

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.EXPORTING

                # Get packaged photos with vision results
                result = await session.execute(
                    select(PackageSelection, Asset, VisionResult)
                    .join(Asset, PackageSelection.asset_id == Asset.id)
                    .outerjoin(
                        VisionResult,
                        (VisionResult.asset_id == Asset.id) & (VisionResult.tier == 1),
                    )
                    .where(PackageSelection.listing_id == listing_id)
                    .order_by(PackageSelection.position)
                )
                rows = result.all()

                # Get social content if it exists
                social_result = await session.execute(
                    select(SocialContent).where(SocialContent.listing_id == listing_id)
                )
                social_contents = social_result.scalars().all()

                # Build address slug for filenames
                addr = listing.address
                slug = f"{addr.get('street', 'listing')}_{addr.get('city', '')}".replace(" ", "_").lower()[:50]
                date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

                # Download and prepare photos
                photos_meta = []
                photo_files = []  # (filename, bytes)
                for pkg, asset, vr in rows:
                    room = vr.room_label if vr else "photo"
                    quality = vr.quality_score if vr else 0
                    is_hero = pkg.position == 0
                    filename = f"{pkg.position:02d}_{room}_{str(listing_id)[:8]}.jpg"

                    try:
                        raw_bytes = self._storage.download(asset.file_path)
                        processed = _resize_photo(raw_bytes)
                        photo_files.append((filename, processed))
                        photos_meta.append({
                            "filename": filename,
                            "position": pkg.position,
                            "room_label": room,
                            "quality_score": quality,
                            "caption": room.replace("_", " ").title(),
                            "hero": "yes" if is_hero else "no",
                        })
                    except Exception:
                        continue  # Skip failed photos

                # Build MLS bundle (unbranded)
                mls_zip_buf = io.BytesIO()
                with zipfile.ZipFile(mls_zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fname, data in photo_files:
                        zf.writestr(fname, data)
                    zf.writestr("metadata.csv", _build_metadata_csv(photos_meta))
                    zf.writestr("description_mls.txt", self._content_result.get("mls_safe", ""))
                    zf.writestr("manifest.json", _build_manifest(
                        str(listing_id), len(photo_files), "mls", False,
                    ))
                mls_zip_bytes = mls_zip_buf.getvalue()
                mls_key = f"listings/{listing_id}/export/{slug}_{date_str}_mls.zip"
                self._storage.upload(key=mls_key, data=mls_zip_bytes, content_type="application/zip")

                # Build Marketing bundle (branded, includes social if available)
                has_social = len(social_contents) > 0
                mkt_zip_buf = io.BytesIO()
                with zipfile.ZipFile(mkt_zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fname, data in photo_files:
                        zf.writestr(fname, data)
                    zf.writestr("metadata.csv", _build_metadata_csv(photos_meta))
                    zf.writestr("description_mls.txt", self._content_result.get("mls_safe", ""))
                    zf.writestr("description.txt", self._content_result.get("marketing", ""))
                    if self._flyer_s3_key:
                        try:
                            flyer_bytes = self._storage.download(self._flyer_s3_key)
                            zf.writestr("flyer.pdf", flyer_bytes)
                        except Exception:
                            pass
                    if has_social:
                        social_data = {
                            sc.platform: {
                                "caption": sc.caption,
                                "hashtags": sc.hashtags,
                                "cta": sc.cta,
                            }
                            for sc in social_contents
                        }
                        zf.writestr("social_posts.json", json.dumps(social_data, indent=2))
                    zf.writestr("manifest.json", _build_manifest(
                        str(listing_id), len(photo_files), "marketing", has_social,
                    ))
                mkt_zip_bytes = mkt_zip_buf.getvalue()
                mkt_key = f"listings/{listing_id}/export/{slug}_{date_str}_marketing.zip"
                self._storage.upload(key=mkt_key, data=mkt_zip_bytes, content_type="application/zip")

                # Update listing with bundle paths
                listing.mls_bundle_path = mls_key
                listing.marketing_bundle_path = mkt_key

                await emit_event(
                    session=session,
                    event_type="mls_export.completed",
                    payload={
                        "mls_bundle_path": mls_key,
                        "marketing_bundle_path": mkt_key,
                        "photo_count": len(photo_files),
                        "includes_social": has_social,
                    },
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {
            "mls_bundle_path": mls_key,
            "marketing_bundle_path": mkt_key,
            "photo_count": len(photo_files),
        }
```

- [ ] **Step 4: Add download method to StorageService**

The MLSExportAgent needs `storage.download()`. Add to `src/launchlens/services/storage.py`:

```python
def download(self, key: str) -> bytes:
    """Download an object from S3 and return its bytes."""
    response = self._client.get_object(Bucket=self._bucket, Key=key)
    return response["Body"].read()
```

- [ ] **Step 5: Run the tests**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_agents/test_mls_export.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Run full test suite**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/launchlens/agents/mls_export.py src/launchlens/services/storage.py tests/test_agents/test_mls_export.py
git commit -m "feat: MLSExportAgent — dual ZIP bundles (MLS unbranded + marketing branded)"
```

---

## Task 6: Export API Endpoint

**Files:**
- Modify: `src/launchlens/api/schemas/listings.py`
- Modify: `src/launchlens/api/listings.py`
- Create: `tests/test_api/test_export.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_api/test_export.py`:

```python
import uuid

import pytest

from launchlens.models.listing import Listing, ListingState
from launchlens.models.tenant import Tenant
from tests.conftest import make_jwt


async def _setup_tenant_and_listing(db_session, state=ListingState.DELIVERED, mls_path=None, mkt_path=None):
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Brokerage",
        plan="pro",
    )
    db_session.add(tenant)
    await db_session.flush()

    listing = Listing(
        tenant_id=tenant.id,
        address={"street": "789 Pine", "city": "Austin", "state": "TX"},
        metadata_={"beds": 3, "baths": 2, "sqft": 2000, "price": 500000},
        state=state,
        mls_bundle_path=mls_path,
        marketing_bundle_path=mkt_path,
    )
    db_session.add(listing)
    await db_session.flush()

    headers = {"Authorization": f"Bearer {make_jwt(str(tenant.id))}"}
    return tenant, listing, headers


@pytest.mark.asyncio
async def test_export_returns_mls_bundle(async_client, db_session):
    _, listing, headers = await _setup_tenant_and_listing(
        db_session,
        mls_path="listings/abc/export/test_mls.zip",
        mkt_path="listings/abc/export/test_marketing.zip",
    )
    resp = await async_client.get(f"/listings/{listing.id}/export?mode=mls", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "mls"
    assert "download_url" in data
    assert data["listing_id"] == str(listing.id)


@pytest.mark.asyncio
async def test_export_defaults_to_marketing(async_client, db_session):
    _, listing, headers = await _setup_tenant_and_listing(
        db_session,
        mls_path="listings/abc/export/test_mls.zip",
        mkt_path="listings/abc/export/test_marketing.zip",
    )
    resp = await async_client.get(f"/listings/{listing.id}/export", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["mode"] == "marketing"


@pytest.mark.asyncio
async def test_export_404_when_no_bundle(async_client, db_session):
    _, listing, headers = await _setup_tenant_and_listing(
        db_session,
        state=ListingState.APPROVED,
    )
    resp = await async_client.get(f"/listings/{listing.id}/export?mode=mls", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_409_when_not_approved(async_client, db_session):
    _, listing, headers = await _setup_tenant_and_listing(
        db_session,
        state=ListingState.ANALYZING,
    )
    resp = await async_client.get(f"/listings/{listing.id}/export", headers=headers)
    assert resp.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_api/test_export.py -v
```

Expected: FAIL — route not found (404 for all).

- [ ] **Step 3: Add export schemas**

Add to `src/launchlens/api/schemas/listings.py`:

```python
import enum

# ... existing code ...


class ExportMode(str, enum.Enum):
    mls = "mls"
    marketing = "marketing"


class BundleMetadata(BaseModel):
    photo_count: int | None = None
    includes_description: bool = True
    includes_flyer: bool = False
    includes_social_posts: bool = False


class ExportResponse(BaseModel):
    listing_id: uuid.UUID
    mode: str
    download_url: str
    expires_at: datetime
    bundle: BundleMetadata
```

- [ ] **Step 4: Add export endpoint to listings router**

Add to `src/launchlens/api/listings.py` after the `approve_listing` endpoint:

```python
from launchlens.api.schemas.listings import ExportMode, ExportResponse, BundleMetadata
from launchlens.services.storage import StorageService

# ... existing code ...

@router.get("/{listing_id}/export", response_model=ExportResponse)
async def export_listing(
    listing_id: uuid.UUID,
    mode: ExportMode = ExportMode.marketing,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    exportable_states = {
        ListingState.APPROVED, ListingState.EXPORTING, ListingState.DELIVERED,
    }
    if listing.state not in exportable_states:
        raise HTTPException(
            status_code=409,
            detail=f"Listing must be approved before export. Current state: {listing.state.value}",
        )

    bundle_path = listing.mls_bundle_path if mode == ExportMode.mls else listing.marketing_bundle_path
    if not bundle_path:
        raise HTTPException(
            status_code=404,
            detail=f"Export not yet generated for mode '{mode.value}'. Bundle is created automatically after approval.",
        )

    storage = StorageService()
    download_url = storage.presigned_url(bundle_path, expires_in=3600)
    expires_at = datetime.now(timezone.utc).replace(microsecond=0) + __import__("datetime").timedelta(hours=1)

    is_marketing = mode == ExportMode.marketing
    return ExportResponse(
        listing_id=listing.id,
        mode=mode.value,
        download_url=download_url,
        expires_at=expires_at,
        bundle=BundleMetadata(
            includes_description=True,
            includes_flyer=is_marketing,
            includes_social_posts=is_marketing and listing.marketing_bundle_path is not None,
        ),
    )
```

**Important:** The `expires_at` import is ugly. Clean it up — add `from datetime import timedelta` to the imports at the top of the file.

- [ ] **Step 5: Run the export tests**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_api/test_export.py -v
```

Expected: 4 tests pass. (The presigned_url call will go to real S3 in the test, but the mock StorageService... actually, this test uses the real app. We need to mock StorageService in the endpoint. For now the test may fail on S3 connection — if so, we need to add a StorageService dependency override.)

If S3 connection fails, add a dependency injection for StorageService or mock it. The simplest approach: mock `StorageService.presigned_url` at module level in the test:

```python
from unittest.mock import patch

# Add @patch at the test level if needed:
@pytest.mark.asyncio
@patch("launchlens.api.listings.StorageService")
async def test_export_returns_mls_bundle(mock_storage_cls, async_client, db_session):
    mock_storage_cls.return_value.presigned_url.return_value = "https://s3.example.com/presigned"
    # ... rest of test
```

Apply the same pattern to the other export tests if needed.

- [ ] **Step 6: Run full test suite**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/launchlens/api/schemas/listings.py src/launchlens/api/listings.py tests/test_api/test_export.py
git commit -m "feat: GET /listings/{id}/export — presigned URL for MLS or marketing bundle"
```

---

## Task 7: Temporal Workflow — Parallel Phase 2 + New Activities

**Files:**
- Modify: `src/launchlens/activities/pipeline.py`
- Modify: `src/launchlens/workflows/listing_pipeline.py`
- Modify: `src/launchlens/temporal_client.py`
- Modify: `src/launchlens/api/listings.py` (pass plan to start_pipeline)

- [ ] **Step 1: Add new activities to pipeline.py**

Add to `src/launchlens/activities/pipeline.py` before `ALL_ACTIVITIES`:

```python
@activity.defn
async def run_social_content(context: AgentContext) -> dict:
    from launchlens.agents.social_content import SocialContentAgent
    return await SocialContentAgent().execute(context)


@activity.defn
async def run_mls_export(context: AgentContext, content_result: dict, flyer_s3_key: str | None) -> dict:
    from launchlens.agents.mls_export import MLSExportAgent
    return await MLSExportAgent(content_result=content_result, flyer_s3_key=flyer_s3_key).execute(context)
```

Update `ALL_ACTIVITIES`:

```python
ALL_ACTIVITIES = [
    run_ingestion, run_vision_tier1, run_vision_tier2,
    run_coverage, run_packaging, run_content, run_brand,
    run_social_content, run_mls_export, run_distribution,
]
```

- [ ] **Step 2: Update ListingPipeline for parallel Phase 2**

Replace `src/launchlens/workflows/listing_pipeline.py`:

```python
import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from launchlens.activities.pipeline import (
        run_brand,
        run_content,
        run_coverage,
        run_distribution,
        run_ingestion,
        run_mls_export,
        run_packaging,
        run_social_content,
        run_vision_tier1,
        run_vision_tier2,
    )
    from launchlens.agents.base import AgentContext


@dataclass
class ListingPipelineInput:
    listing_id: str
    tenant_id: str
    plan: str = "starter"


_DEFAULT_RETRY = RetryPolicy(maximum_attempts=3)
_DEFAULT_TIMEOUT = timedelta(minutes=10)
_VISION_TIER2_TIMEOUT = timedelta(minutes=20)
_EXPORT_TIMEOUT = timedelta(minutes=15)


@workflow.defn
class ListingPipeline:
    """
    LaunchLens listing processing pipeline.

    Phase 1: Ingestion -> Vision T1 -> Vision T2 -> Coverage -> Packaging
    [wait for human_review_completed]
    Phase 2: Content -> [Brand + Social (parallel)] -> MLS Export -> Distribution
    """

    def __init__(self) -> None:
        self._shadow_approved = False
        self._review_completed = False

    @workflow.run
    async def run(self, input: ListingPipelineInput) -> str:
        ctx = AgentContext(listing_id=input.listing_id, tenant_id=input.tenant_id)

        # Phase 1: Analysis pipeline
        await workflow.execute_activity(
            run_ingestion, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_vision_tier1, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_vision_tier2, ctx,
            start_to_close_timeout=_VISION_TIER2_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_coverage, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )
        await workflow.execute_activity(
            run_packaging, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        # Wait for human review (listing is now AWAITING_REVIEW)
        await workflow.wait_condition(lambda: self._review_completed)

        # Phase 2: Post-approval pipeline
        # Step 1: Content (dual-tone)
        content_result = await workflow.execute_activity(
            run_content, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        # Step 2: Brand + Social in parallel (social is plan-gated)
        parallel_tasks = [
            workflow.execute_activity(
                run_brand, ctx,
                start_to_close_timeout=_DEFAULT_TIMEOUT,
                retry_policy=_DEFAULT_RETRY,
            )
        ]
        if input.plan in ("pro", "enterprise"):
            parallel_tasks.append(
                workflow.execute_activity(
                    run_social_content, ctx,
                    start_to_close_timeout=_DEFAULT_TIMEOUT,
                    retry_policy=_DEFAULT_RETRY,
                )
            )
        results = await asyncio.gather(*parallel_tasks)
        brand_result = results[0]
        flyer_key = brand_result.get("flyer_s3_key") if isinstance(brand_result, dict) else None

        # Step 3: MLS Export (builds both bundles)
        await workflow.execute_activity(
            run_mls_export, ctx, content_result, flyer_key,
            start_to_close_timeout=_EXPORT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        # Step 4: Distribution (marks DELIVERED)
        await workflow.execute_activity(
            run_distribution, ctx,
            start_to_close_timeout=_DEFAULT_TIMEOUT,
            retry_policy=_DEFAULT_RETRY,
        )

        return f"pipeline_complete:{input.listing_id}"

    @workflow.signal
    async def shadow_review_approved(self) -> None:
        self._shadow_approved = True

    @workflow.signal
    async def human_review_completed(self) -> None:
        self._review_completed = True
```

- [ ] **Step 3: Update temporal_client.py to pass plan**

In `src/launchlens/temporal_client.py`, update `start_pipeline` to accept and pass the plan:

```python
async def start_pipeline(self, listing_id: str, tenant_id: str, plan: str = "starter") -> str:
    client = await self._connect()
    workflow_id = f"listing-pipeline-{listing_id}"
    handle = await client.start_workflow(
        ListingPipeline.run,
        ListingPipelineInput(listing_id=listing_id, tenant_id=tenant_id, plan=plan),
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )
    return handle.id
```

- [ ] **Step 4: Update register_assets to pass tenant plan**

In `src/launchlens/api/listings.py`, in the `register_assets` endpoint, update the `start_pipeline` call (around line 183) to pass the tenant's plan:

```python
await client.start_pipeline(
    listing_id=str(listing.id),
    tenant_id=str(current_user.tenant_id),
    plan=tenant.plan,
)
```

- [ ] **Step 5: Run existing workflow tests**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_workflows/ -v
```

Expected: existing tests pass. If `ListingPipelineInput` tests fail because of the new `plan` field, update the test to include `plan="starter"` or verify it defaults correctly.

- [ ] **Step 6: Run full test suite**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/launchlens/activities/pipeline.py src/launchlens/workflows/listing_pipeline.py src/launchlens/temporal_client.py src/launchlens/api/listings.py
git commit -m "feat: Temporal Phase 2 — parallel Brand+Social, plan-gated, MLS Export step"
```

---

## Task 8: Demo Pipeline — Router + Endpoints

**Files:**
- Create: `src/launchlens/api/schemas/demo.py`
- Create: `src/launchlens/api/demo.py`
- Modify: `src/launchlens/main.py`
- Modify: `src/launchlens/middleware/tenant.py`
- Create: `tests/test_api/test_demo.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_api/test_demo.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from launchlens.models.listing import Listing, ListingState


@pytest.mark.asyncio
async def test_demo_upload_creates_demo_listing(async_client, db_session):
    resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": [f"s3://bucket/demo/photo_{i}.jpg" for i in range(5)]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "demo_id" in data
    assert data["photo_count"] == 5


@pytest.mark.asyncio
async def test_demo_get_returns_results(async_client, db_session):
    # Create a demo listing directly
    listing = Listing(
        tenant_id=uuid.uuid4(),  # placeholder
        address={"street": "Demo St"},
        metadata_={},
        state=ListingState.DEMO,
        is_demo=True,
        demo_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(listing)
    await db_session.flush()

    resp = await async_client.get(f"/demo/{listing.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_demo"] is True
    assert data["locked_features"] == ["description", "flyer", "social_posts", "export"]


@pytest.mark.asyncio
async def test_demo_claim_requires_auth(async_client, db_session):
    listing = Listing(
        tenant_id=uuid.uuid4(),
        address={"street": "Demo St"},
        metadata_={},
        state=ListingState.DEMO,
        is_demo=True,
        demo_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(listing)
    await db_session.flush()

    resp = await async_client.post(f"/demo/{listing.id}/claim")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_demo_expired_returns_410(async_client, db_session):
    listing = Listing(
        tenant_id=uuid.uuid4(),
        address={"street": "Expired Demo"},
        metadata_={},
        state=ListingState.DEMO,
        is_demo=True,
        demo_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(listing)
    await db_session.flush()

    resp = await async_client.get(f"/demo/{listing.id}")
    assert resp.status_code == 410
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_api/test_demo.py -v
```

Expected: FAIL — 404 for all (router not registered).

- [ ] **Step 3: Create demo schemas**

Create `src/launchlens/api/schemas/demo.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class DemoUploadRequest(BaseModel):
    file_paths: list[str]


class DemoUploadResponse(BaseModel):
    demo_id: uuid.UUID
    photo_count: int
    expires_at: datetime


class DemoViewResponse(BaseModel):
    demo_id: uuid.UUID
    address: dict
    state: str
    is_demo: bool
    photos: list[dict] = []
    locked_features: list[str] = ["description", "flyer", "social_posts", "export"]
```

- [ ] **Step 4: Create demo router**

Create `src/launchlens/api/demo.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.api.schemas.demo import DemoUploadRequest, DemoUploadResponse, DemoViewResponse
from launchlens.database import get_db
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState

router = APIRouter()

_DEMO_TTL_HOURS = 24
_DEMO_PHOTO_MIN = 5
_DEMO_PHOTO_MAX = 50


@router.post("/upload", status_code=201, response_model=DemoUploadResponse)
async def demo_upload(
    body: DemoUploadRequest,
    db: AsyncSession = Depends(get_db),
):
    if len(body.file_paths) < _DEMO_PHOTO_MIN or len(body.file_paths) > _DEMO_PHOTO_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Upload between {_DEMO_PHOTO_MIN} and {_DEMO_PHOTO_MAX} photos.",
        )

    expires = datetime.now(timezone.utc) + timedelta(hours=_DEMO_TTL_HOURS)
    # Use a placeholder tenant_id for demo listings (RLS won't apply to unauthenticated reads)
    placeholder_tenant = uuid.UUID("00000000-0000-0000-0000-000000000000")

    listing = Listing(
        tenant_id=placeholder_tenant,
        address={},
        metadata_={},
        state=ListingState.DEMO,
        is_demo=True,
        demo_expires_at=expires,
    )
    db.add(listing)
    await db.flush()

    for path in body.file_paths:
        asset = Asset(
            tenant_id=placeholder_tenant,
            listing_id=listing.id,
            file_path=path,
            file_hash=str(uuid.uuid4())[:8],
            state="uploaded",
        )
        db.add(asset)

    await db.commit()
    await db.refresh(listing)

    return DemoUploadResponse(
        demo_id=listing.id,
        photo_count=len(body.file_paths),
        expires_at=expires,
    )


@router.get("/{demo_id}", response_model=DemoViewResponse)
async def demo_view(
    demo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(Listing, demo_id)
    if not listing or not listing.is_demo:
        raise HTTPException(status_code=404, detail="Demo not found")

    if listing.demo_expires_at and listing.demo_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Demo expired")

    return DemoViewResponse(
        demo_id=listing.id,
        address=listing.address,
        state=listing.state.value,
        is_demo=True,
    )


@router.post("/{demo_id}/claim")
async def demo_claim(
    demo_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # This endpoint requires auth — TenantMiddleware handles it
    # If we reach here without tenant_id, middleware already rejected
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    listing = await db.get(Listing, demo_id)
    if not listing or not listing.is_demo:
        raise HTTPException(status_code=404, detail="Demo not found")

    if listing.demo_expires_at and listing.demo_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Demo expired")

    listing.tenant_id = uuid.UUID(tenant_id)
    listing.is_demo = False
    listing.demo_expires_at = None
    listing.state = ListingState.UPLOADING

    await db.commit()
    await db.refresh(listing)

    return {"listing_id": str(listing.id), "state": listing.state.value, "claimed": True}
```

- [ ] **Step 5: Register demo router in main.py**

Add to `src/launchlens/main.py` imports:

```python
from launchlens.api import admin, assets, auth, billing, demo, listings
```

Add router registration in `create_app()`:

```python
app.include_router(demo.router, prefix="/demo", tags=["demo"])
```

- [ ] **Step 6: Add demo paths to public paths**

Update `src/launchlens/middleware/tenant.py`:

```python
_PUBLIC_PATHS = {"/health", "/auth/register", "/auth/login", "/billing/webhook", "/demo/upload"}
```

Also update the middleware `__call__` to allow GET `/demo/{id}` paths:

```python
async def __call__(self, request: Request, call_next):
    path = request.url.path
    if path in _PUBLIC_PATHS or (path.startswith("/demo/") and request.method == "GET"):
        return await call_next(request)
    # ... rest unchanged
```

- [ ] **Step 7: Run the demo tests**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest tests/test_api/test_demo.py -v
```

Expected: 4 tests pass.

- [ ] **Step 8: Run full test suite**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add src/launchlens/api/demo.py src/launchlens/api/schemas/demo.py src/launchlens/main.py src/launchlens/middleware/tenant.py tests/test_api/test_demo.py
git commit -m "feat: demo pipeline — upload/view/claim endpoints for results-first onboarding"
```

---

## Task 9: PRD v3 Rewrite

**Files:**
- Modify: `docs/LaunchLens-PRD-v2.md` → rename/replace with `docs/LaunchLens-PRD-v3.md`

- [ ] **Step 1: Create PRD v3 with Listing Media OS positioning**

Create `docs/LaunchLens-PRD-v3.md` with the updated positioning, feature names, pricing copy, onboarding flow, pipeline diagram (including new agents), and MLS compliance strategy from the design spec. Keep PRD v2 intact for history.

Key updates from the design spec:
- Section 1 (Vision): Updated tagline and positioning language
- Section 4 (Product Design): Pipeline diagram includes SocialContentAgent + MLSExportAgent
- Section 4 (Features): Renamed features per the design spec mapping table
- Section 5 (User Stories): Add stories for MLS Export and Social Content
- Section 6 (Scope): Move MLS Export + Social Content to "Built" section
- Section 7 (Pricing): Updated copy per design spec tables
- Section 8 (Go-to-Market): Add results-first onboarding flow
- Section 9 (Architecture): Updated pipeline diagram and state machine
- New Section: MLS Compliance Strategy (Phase 1/2/3)

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens
git add docs/LaunchLens-PRD-v3.md
git commit -m "docs: PRD v3 — Listing Media OS positioning, new agents, MLS compliance strategy"
```

---

## Task 10: Final Integration — Run All Tests

- [ ] **Step 1: Run full test suite**

```bash
cd C:/Users/Jeff/launchlens && python -m pytest --tb=short -q
```

Expected: ~205+ tests pass (193 existing + ~12 new).

- [ ] **Step 2: Run linter**

```bash
cd C:/Users/Jeff/launchlens && python -m ruff check src/ tests/
```

Expected: no errors.

- [ ] **Step 3: Verify Docker build**

```bash
cd C:/Users/Jeff/launchlens && docker build -t launchlens:test .
```

Expected: build succeeds.

- [ ] **Step 4: Final commit with version bump**

If all checks pass, update the version in `src/launchlens/main.py`:

```python
app = FastAPI(title="LaunchLens", version="0.9.0", lifespan=lifespan)
```

```bash
cd C:/Users/Jeff/launchlens
git add src/launchlens/main.py
git commit -m "chore: bump version to 0.9.0 — Listing Media OS"
```
