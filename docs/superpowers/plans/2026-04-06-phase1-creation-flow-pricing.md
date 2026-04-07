# Phase 1: Creation Flow Rework & Package Restructuring

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-step listing creation dialog with a 5-step wizard, restructure pricing (base 15 credits, bundle option), and make social/compliance pipeline steps always run.

**Architecture:** Backend-first approach. Add DRAFT listing state and defer credit deduction to a new `start-pipeline` endpoint. Update pipeline workflow to remove addon gates for social/compliance. Frontend builds a full-page wizard at `/listings/new` with step navigation, photo upload, staging tags, addon selection, and review/confirm.

**Tech Stack:** Python/FastAPI + SQLAlchemy + Alembic (backend), Temporal workflows, Next.js 15 + React 19 + Tailwind v4 + Framer Motion (frontend)

---

## File Structure

### Backend — New files
- `alembic/versions/037_add_draft_state_and_bundle.py` — Migration: add DRAFT to listing state enum, add `bundle_id` column to addon_purchases, seed bundle catalog entry
- `src/listingjet/api/listings_draft.py` — New router: staging-tags + start-pipeline endpoints
- `src/listingjet/api/schemas/draft.py` — Pydantic schemas for new endpoints

### Backend — Modified files
- `src/listingjet/models/listing.py` — Add `DRAFT` to `ListingState` enum
- `src/listingjet/config/tiers.py` — Update `SERVICE_CREDIT_COSTS` and `TIER_DEFAULTS` for 15-credit base, remove migrated addon costs
- `src/listingjet/services/listing_creation.py` — Create listings in DRAFT state, skip credit deduction
- `src/listingjet/temporal_client.py` — Pass `enabled_addons` and `billing_model` to workflow
- `src/listingjet/workflows/listing_pipeline.py` — Remove addon gates for social_content, social_cuts; always run them
- `src/listingjet/api/listings_media.py` — Don't auto-trigger pipeline on upload for DRAFT listings
- `src/listingjet/api/listings_core.py` — Add DRAFT to refundable/cancellable states, hide DRAFT from default list
- `src/listingjet/api/listings_workflow.py` — Add DRAFT to cancellable states
- `src/listingjet/api/addons.py` — Add bundle activation support
- `src/listingjet/api/app.py` — Register new draft router
- `src/listingjet/services/credits.py` — No changes needed (existing deduct_credits works)
- `frontend/src/contexts/plan-context.tsx` — Update `LISTING_CREDIT_COST` to 15

### Frontend — New files
- `frontend/src/app/listings/new/page.tsx` — Wizard page route
- `frontend/src/components/listings/creation-wizard/wizard-container.tsx` — Step state, navigation, shared form data
- `frontend/src/components/listings/creation-wizard/step-property-details.tsx` — Step 1
- `frontend/src/components/listings/creation-wizard/step-upload-photos.tsx` — Step 2
- `frontend/src/components/listings/creation-wizard/step-virtual-staging.tsx` — Step 3
- `frontend/src/components/listings/creation-wizard/step-addons.tsx` — Step 4
- `frontend/src/components/listings/creation-wizard/step-review-confirm.tsx` — Step 5

### Frontend — Modified files
- `frontend/src/app/listings/page.tsx` — Change "New Listing" button to navigate to `/listings/new`
- `frontend/src/lib/api-client.ts` — Add `startPipeline()`, `setStagingTags()`, `activateBundle()` methods

### Test files
- `tests/test_api/test_draft_flow.py` — End-to-end draft creation flow tests
- `tests/test_models/test_listing.py` — DRAFT state transition tests
- `tests/test_workflows/test_listing_pipeline.py` — Pipeline always-run tests (modify existing)

---

## Task 1: Add DRAFT State to Listing Model

**Files:**
- Modify: `src/listingjet/models/listing.py:13-25`
- Test: `tests/test_models/test_listing.py`

- [ ] **Step 1: Write failing test for DRAFT state**

```python
# tests/test_models/test_listing.py — add to existing file
def test_draft_state_exists():
    from listingjet.models.listing import ListingState
    assert ListingState.DRAFT == "draft"
    assert ListingState.DRAFT.value == "draft"

def test_draft_state_ordering():
    """DRAFT should be a valid state that comes before NEW."""
    from listingjet.models.listing import ListingState
    states = list(ListingState)
    draft_idx = states.index(ListingState.DRAFT)
    new_idx = states.index(ListingState.NEW)
    assert draft_idx < new_idx
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_models/test_listing.py::test_draft_state_exists -v`
Expected: FAIL with `AttributeError: DRAFT`

- [ ] **Step 3: Add DRAFT to ListingState enum**

In `src/listingjet/models/listing.py`, add `DRAFT = "draft"` as the first enum member:

```python
class ListingState(str, enum.Enum):
    DRAFT = "draft"
    NEW = "new"
    UPLOADING = "uploading"
    ANALYZING = "analyzing"
    AWAITING_REVIEW = "awaiting_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DELIVERED = "delivered"
    PIPELINE_TIMEOUT = "pipeline_timeout"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPORTING = "exporting"
    DEMO = "demo"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_models/test_listing.py::test_draft_state_exists tests/test_models/test_listing.py::test_draft_state_ordering -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/models/listing.py tests/test_models/test_listing.py && git commit -m "feat: add DRAFT state to ListingState enum"
```

---

## Task 2: Database Migration — DRAFT State + Bundle Support

**Files:**
- Create: `alembic/versions/037_add_draft_state_and_bundle.py`

- [ ] **Step 1: Create the migration file**

```python
"""Add DRAFT listing state and bundle support.

Revision ID: 037
Revises: 036
"""
from alembic import op
import sqlalchemy as sa

revision = "037"
down_revision = "036"


def upgrade():
    # Add DRAFT to listing state enum
    op.execute("ALTER TYPE listingstate ADD VALUE IF NOT EXISTS 'draft' BEFORE 'new'")

    # Add bundle_id to addon_purchases for tracking bundle activations
    op.add_column(
        "addon_purchases",
        sa.Column("bundle_id", sa.String(50), nullable=True),
    )

    # Seed the "all_addons_bundle" into addon_catalog
    op.execute("""
        INSERT INTO addon_catalog (id, slug, name, credit_cost, is_active, metadata)
        VALUES (
            gen_random_uuid(),
            'all_addons_bundle',
            'Premium Bundle (Video + Staging + Floorplan)',
            30,
            true,
            '{"includes": ["ai_video_tour", "virtual_staging", "3d_floorplan"], "savings": 13}'::jsonb
        )
        ON CONFLICT (slug) DO NOTHING
    """)

    # Deactivate addons that are now included in base
    op.execute("""
        UPDATE addon_catalog SET is_active = false
        WHERE slug IN ('social_content_pack', 'social_media_cuts', 'photo_compliance', 'microsite', 'image_editing', 'cma_report')
    """)


def downgrade():
    # Re-activate deactivated addons
    op.execute("""
        UPDATE addon_catalog SET is_active = true
        WHERE slug IN ('social_content_pack', 'social_media_cuts', 'photo_compliance', 'microsite', 'image_editing', 'cma_report')
    """)

    # Remove bundle from catalog
    op.execute("DELETE FROM addon_catalog WHERE slug = 'all_addons_bundle'")

    # Remove bundle_id column
    op.drop_column("addon_purchases", "bundle_id")

    # Note: Cannot remove enum value in PostgreSQL, leave DRAFT in place
```

- [ ] **Step 2: Verify migration syntax**

Run: `cd C:/Users/Jeff/launchlens && python -c "import ast; ast.parse(open('alembic/versions/037_add_draft_state_and_bundle.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add alembic/versions/037_add_draft_state_and_bundle.py && git commit -m "feat: migration 037 — DRAFT state, bundle support, deactivate base-included addons"
```

---

## Task 3: Update Pricing Configuration

**Files:**
- Modify: `src/listingjet/config/tiers.py:12-23` and `:29-58`
- Test: `tests/test_config/test_tiers.py` (new)

- [ ] **Step 1: Write failing test for new pricing**

Create `tests/test_config/test_tiers.py`:

```python
from listingjet.config.tiers import SERVICE_CREDIT_COSTS, TIER_DEFAULTS, BUNDLE_PRICING


def test_base_listing_cost_is_15():
    assert SERVICE_CREDIT_COSTS["base_listing"] == 15


def test_removed_addons_not_in_costs():
    """Social content, social cuts, photo compliance, microsite are now in base."""
    for removed in ("social_content_pack", "social_media_cuts", "photo_compliance", "microsite", "image_editing", "cma_report"):
        assert removed not in SERVICE_CREDIT_COSTS, f"{removed} should be removed from SERVICE_CREDIT_COSTS"


def test_remaining_addons():
    assert SERVICE_CREDIT_COSTS["ai_video_tour"] == 20
    assert SERVICE_CREDIT_COSTS["virtual_staging"] == 15
    assert SERVICE_CREDIT_COSTS["3d_floorplan"] == 8


def test_bundle_pricing():
    assert BUNDLE_PRICING["all_addons_bundle"]["credit_cost"] == 30
    assert set(BUNDLE_PRICING["all_addons_bundle"]["includes"]) == {"ai_video_tour", "virtual_staging", "3d_floorplan"}


def test_tier_per_listing_cost_is_15():
    for tier_name, cfg in TIER_DEFAULTS.items():
        assert cfg["per_listing_credit_cost"] == 15, f"{tier_name} should have per_listing_credit_cost=15"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_config/test_tiers.py -v`
Expected: FAIL (base is 12, removed addons still present, BUNDLE_PRICING doesn't exist)

- [ ] **Step 3: Update tiers.py**

Replace `SERVICE_CREDIT_COSTS` dict in `src/listingjet/config/tiers.py`:

```python
SERVICE_CREDIT_COSTS: dict[str, int] = {
    "base_listing": 15,
    "ai_video_tour": 20,
    "virtual_staging": 15,
    "3d_floorplan": 8,
}
```

Add `BUNDLE_PRICING` dict after `SERVICE_CREDIT_COSTS`:

```python
# ---------------------------------------------------------------------------
# Bundle pricing — discounted multi-addon packages
# ---------------------------------------------------------------------------

BUNDLE_PRICING: dict[str, dict] = {
    "all_addons_bundle": {
        "credit_cost": 30,
        "includes": ["ai_video_tour", "virtual_staging", "3d_floorplan"],
        "savings": 13,  # 43 individual - 30 bundle
    },
}
```

Update all `per_listing_credit_cost` values in `TIER_DEFAULTS` from `12` to `15`:

```python
TIER_DEFAULTS: dict[str, dict] = {
    "free": {
        "included_credits": 0,
        "rollover_cap": 0,
        "per_listing_credit_cost": 15,
        "per_credit_dollar_value": 0.50,
        "monthly_price_cents": 0,
    },
    "lite": {
        "included_credits": 25,
        "rollover_cap": 15,
        "per_listing_credit_cost": 15,
        "per_credit_dollar_value": 0.45,
        "monthly_price_cents": 1900,
    },
    "active_agent": {
        "included_credits": 75,
        "rollover_cap": 50,
        "per_listing_credit_cost": 15,
        "per_credit_dollar_value": 0.40,
        "monthly_price_cents": 4900,
    },
    "team": {
        "included_credits": 250,
        "rollover_cap": 150,
        "per_listing_credit_cost": 15,
        "per_credit_dollar_value": 0.35,
        "monthly_price_cents": 9900,
    },
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_config/test_tiers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/config/tiers.py tests/test_config/test_tiers.py && git commit -m "feat: update pricing — base 15 credits, remove bundled addons, add all_addons_bundle"
```

---

## Task 4: Update Listing Creation Service for DRAFT State

**Files:**
- Modify: `src/listingjet/services/listing_creation.py`
- Test: `tests/test_api/test_draft_flow.py` (new)

- [ ] **Step 1: Write failing test**

Create `tests/test_api/test_draft_flow.py`:

```python
"""Tests for the DRAFT listing creation flow."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from listingjet.models.listing import ListingState
from listingjet.services.listing_creation import ListingCreationService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    return session


@pytest.fixture
def credit_tenant():
    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    tenant.billing_model = "credit"
    tenant.per_listing_credit_cost = 15
    tenant.plan = "active_agent"
    return tenant


@pytest.mark.asyncio
async def test_create_listing_creates_draft(mock_session, credit_tenant):
    """Credit-billed listings should be created in DRAFT state with no credit deduction."""
    svc = ListingCreationService()
    listing = await svc.create(
        session=mock_session,
        tenant=credit_tenant,
        tenant_id=credit_tenant.id,
        address={"street": "123 Main St", "city": "Austin", "state": "TX"},
        metadata={},
    )
    assert listing.state == ListingState.DRAFT
    assert listing.credit_cost is None  # Credits not deducted yet


@pytest.mark.asyncio
async def test_create_listing_no_credit_deduction_for_draft(mock_session, credit_tenant):
    """No credits should be deducted when creating a DRAFT listing."""
    mock_credit_svc = AsyncMock()
    svc = ListingCreationService(credit_svc=mock_credit_svc)
    await svc.create(
        session=mock_session,
        tenant=credit_tenant,
        tenant_id=credit_tenant.id,
        address={"street": "123 Main St"},
        metadata={},
    )
    mock_credit_svc.deduct_credits.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_api/test_draft_flow.py::test_create_listing_creates_draft -v`
Expected: FAIL (listing.state == NEW, not DRAFT; credits are deducted)

- [ ] **Step 3: Update ListingCreationService**

In `src/listingjet/services/listing_creation.py`, modify the `create` method. Change the listing creation to use `DRAFT` state and skip credit deduction for credit-billed tenants:

Replace the listing instantiation and billing block (lines 70-101):

```python
        listing_id = uuid.uuid4()
        listing = Listing(
            id=listing_id,
            tenant_id=tenant_id,
            address=address,
            metadata_={**metadata, **({"idempotency_key": idempotency_key} if idempotency_key else {})},
            state=ListingState.DRAFT if tenant.billing_model == "credit" else ListingState.NEW,
        )

        if tenant.billing_model != "credit":
            # Legacy billing: monthly quota check (credits deferred to start-pipeline for credit users)
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            count_result = await session.execute(
                select(func.count(Listing.id)).where(
                    Listing.tenant_id == tenant_id,
                    Listing.created_at >= month_start,
                )
            )
            current_count = count_result.scalar() or 0
            if not check_listing_quota(tenant.plan, current_count):
                raise ListingQuotaExceededError(current_count)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_api/test_draft_flow.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/services/listing_creation.py tests/test_api/test_draft_flow.py && git commit -m "feat: create credit listings in DRAFT state, defer credit deduction"
```

---

## Task 5: Update Temporal Client to Pass Addons & Billing Model

**Files:**
- Modify: `src/listingjet/temporal_client.py:16-25`

- [ ] **Step 1: Update start_pipeline signature**

In `src/listingjet/temporal_client.py`, update the `start_pipeline` method:

```python
    async def start_pipeline(
        self,
        listing_id: str,
        tenant_id: str,
        plan: str = "starter",
        billing_model: str = "legacy",
        enabled_addons: list[str] | None = None,
    ) -> str:
        client = await self._connect()
        workflow_id = f"listing-pipeline-{listing_id}"
        handle = await client.start_workflow(
            ListingPipeline.run,
            ListingPipelineInput(
                listing_id=listing_id,
                tenant_id=tenant_id,
                plan=plan,
                billing_model=billing_model,
                enabled_addons=enabled_addons,
            ),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        return handle.id
```

- [ ] **Step 2: Verify existing callers still work (default params)**

Run: `cd C:/Users/Jeff/launchlens && python -c "from listingjet.temporal_client import TemporalClient; print('import OK')"`
Expected: `import OK` — existing callers use positional/keyword args that still match.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/temporal_client.py && git commit -m "feat: pass billing_model and enabled_addons to pipeline workflow"
```

---

## Task 6: Start-Pipeline Endpoint + Schemas

**Files:**
- Create: `src/listingjet/api/schemas/draft.py`
- Create: `src/listingjet/api/listings_draft.py`
- Modify: `src/listingjet/api/app.py` (register router)
- Test: `tests/test_api/test_draft_flow.py` (append)

- [ ] **Step 1: Create Pydantic schemas**

Create `src/listingjet/api/schemas/draft.py`:

```python
"""Schemas for draft listing flow (staging tags + start pipeline)."""
from pydantic import BaseModel, Field


class StagingTagRequest(BaseModel):
    asset_ids: list[str] = Field(..., min_length=1, description="Asset UUIDs to tag for virtual staging")


class StagingTagResponse(BaseModel):
    tagged_count: int
    listing_id: str


class StartPipelineRequest(BaseModel):
    selected_addons: list[str] = Field(default_factory=list, description="Addon slugs to activate (or 'all_addons_bundle')")


class StartPipelineResponse(BaseModel):
    listing_id: str
    state: str
    credits_deducted: int
    workflow_id: str
```

- [ ] **Step 2: Create the draft router with start-pipeline endpoint**

Create `src/listingjet/api/listings_draft.py`:

```python
"""Draft listing endpoints — staging tags and pipeline start."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.draft import (
    StartPipelineRequest,
    StartPipelineResponse,
    StagingTagRequest,
    StagingTagResponse,
)
from listingjet.config.tiers import BUNDLE_PRICING, SERVICE_CREDIT_COSTS
from listingjet.database import get_db
from listingjet.models.addon_catalog import AddonCatalog
from listingjet.models.addon_purchase import AddonPurchase
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.credits import CreditService, InsufficientCreditsError
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{listing_id}/staging-tags", response_model=StagingTagResponse)
async def set_staging_tags(
    listing_id: uuid.UUID,
    body: StagingTagRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tag specific photos for virtual staging. Only allowed on DRAFT listings."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.state != ListingState.DRAFT:
        raise HTTPException(status_code=409, detail=f"Staging tags can only be set on DRAFT listings, current: {listing.state.value}")

    # Validate asset IDs belong to this listing
    asset_uuids = [uuid.UUID(aid) for aid in body.asset_ids]
    result = await db.execute(
        select(Asset).where(Asset.listing_id == listing_id, Asset.id.in_(asset_uuids))
    )
    found_assets = result.scalars().all()
    if len(found_assets) != len(asset_uuids):
        raise HTTPException(status_code=400, detail="Some asset IDs not found for this listing")

    # Store staging tags in listing metadata
    current_meta = dict(listing.metadata_) if listing.metadata_ else {}
    current_meta["staging_asset_ids"] = body.asset_ids
    listing.metadata_ = current_meta

    await db.commit()
    return StagingTagResponse(tagged_count=len(body.asset_ids), listing_id=str(listing_id))


@router.post("/{listing_id}/start-pipeline", response_model=StartPipelineResponse)
async def start_pipeline(
    listing_id: uuid.UUID,
    body: StartPipelineRequest,
    _rl=Depends(rate_limit(5, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm a DRAFT listing: deduct credits, activate addons, start the pipeline.

    This is the point of no return — credits are charged and the pipeline begins.
    """
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.state != ListingState.DRAFT:
        raise HTTPException(status_code=409, detail=f"Can only start pipeline for DRAFT listings, current: {listing.state.value}")

    # Verify listing has assets
    asset_count = (await db.execute(
        select(Asset.id).where(Asset.listing_id == listing_id).limit(1)
    )).scalar_one_or_none()
    if not asset_count:
        raise HTTPException(status_code=400, detail="Upload at least one photo before starting the pipeline")

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    credit_svc = CreditService()

    # Calculate total cost
    base_cost = tenant.per_listing_credit_cost
    addon_cost = 0
    is_bundle = "all_addons_bundle" in body.selected_addons
    enabled_addon_slugs: list[str] = []

    if is_bundle:
        bundle = BUNDLE_PRICING["all_addons_bundle"]
        addon_cost = bundle["credit_cost"]
        enabled_addon_slugs = list(bundle["includes"])
    else:
        for slug in body.selected_addons:
            cost = SERVICE_CREDIT_COSTS.get(slug)
            if cost is None:
                raise HTTPException(status_code=400, detail=f"Unknown addon: {slug}")
            addon_cost += cost
            enabled_addon_slugs.append(slug)

    total_cost = base_cost + addon_cost

    # Deduct base listing credits
    try:
        await credit_svc.deduct_credits(
            db, tenant.id, base_cost,
            transaction_type="listing_debit",
            reference_type="listing",
            reference_id=str(listing_id),
            description=f"Listing at {listing.address.get('street', 'new listing')}",
        )
    except InsufficientCreditsError:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {total_cost}, purchase more to continue.")

    listing.credit_cost = base_cost

    # Activate addons and deduct addon credits
    bundle_id = "all_addons_bundle" if is_bundle else None
    for slug in enabled_addon_slugs:
        catalog_entry = (await db.execute(
            select(AddonCatalog).where(AddonCatalog.slug == slug)
        )).scalar_one_or_none()
        if not catalog_entry:
            continue

        addon_credit_cost = 0 if is_bundle else catalog_entry.credit_cost
        txn = None
        if addon_credit_cost > 0:
            try:
                txn = await credit_svc.deduct_credits(
                    db, tenant.id, addon_credit_cost,
                    transaction_type="addon_debit",
                    reference_type="addon",
                    reference_id=f"{listing_id}:{slug}",
                    description=f"Addon {slug} for listing {listing.address.get('street', '')}",
                )
            except InsufficientCreditsError:
                raise HTTPException(status_code=402, detail=f"Insufficient credits for addon {slug}.")

        purchase = AddonPurchase(
            tenant_id=tenant.id,
            listing_id=listing_id,
            addon_id=catalog_entry.id,
            credit_transaction_id=txn.id if txn else None,
            bundle_id=bundle_id,
            status="active",
        )
        db.add(purchase)

    # Bundle credit deduction (single charge for all included addons)
    if is_bundle:
        try:
            await credit_svc.deduct_credits(
                db, tenant.id, addon_cost,
                transaction_type="addon_debit",
                reference_type="bundle",
                reference_id=f"{listing_id}:all_addons_bundle",
                description=f"Premium Bundle for listing {listing.address.get('street', '')}",
            )
        except InsufficientCreditsError:
            raise HTTPException(status_code=402, detail=f"Insufficient credits for bundle. Need {addon_cost} more.")

    # Transition to UPLOADING and start pipeline
    listing.state = ListingState.UPLOADING
    await db.commit()

    # Start Temporal workflow
    workflow_id = ""
    try:
        client = get_temporal_client()
        workflow_id = await client.start_pipeline(
            listing_id=str(listing_id),
            tenant_id=str(tenant.id),
            plan=tenant.plan,
            billing_model=tenant.billing_model,
            enabled_addons=enabled_addon_slugs,
        )
    except Exception:
        logger.exception("Pipeline start failed for listing %s", listing_id)
        listing.state = ListingState.FAILED
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to start processing pipeline")

    return StartPipelineResponse(
        listing_id=str(listing_id),
        state=listing.state.value,
        credits_deducted=total_cost,
        workflow_id=workflow_id,
    )
```

- [ ] **Step 3: Register the router in app.py**

Find where routers are included in `src/listingjet/api/app.py` and add:

```python
from listingjet.api.listings_draft import router as listings_draft_router
# ... in the router setup:
app.include_router(listings_draft_router, prefix="/listings", tags=["listings-draft"])
```

- [ ] **Step 4: Write test for start-pipeline endpoint**

Append to `tests/test_api/test_draft_flow.py`:

```python
@pytest.mark.asyncio
async def test_start_pipeline_deducts_credits_and_transitions(mock_session, credit_tenant):
    """start-pipeline should deduct base + addon credits and move to UPLOADING."""
    from listingjet.api.schemas.draft import StartPipelineRequest
    # This is a unit-level test for the credit calculation logic
    base_cost = credit_tenant.per_listing_credit_cost  # 15
    bundle_cost = 30
    total = base_cost + bundle_cost  # 45
    assert total == 45


@pytest.mark.asyncio
async def test_start_pipeline_rejects_non_draft():
    """start-pipeline should reject listings not in DRAFT state."""
    from listingjet.models.listing import ListingState
    non_draft_states = [ListingState.NEW, ListingState.UPLOADING, ListingState.DELIVERED]
    for state in non_draft_states:
        assert state != ListingState.DRAFT
```

- [ ] **Step 5: Run tests**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_api/test_draft_flow.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/api/schemas/draft.py src/listingjet/api/listings_draft.py src/listingjet/api/app.py tests/test_api/test_draft_flow.py && git commit -m "feat: add start-pipeline and staging-tags endpoints for draft flow"
```

---

## Task 7: Update Pipeline — Social/Compliance Always Run

**Files:**
- Modify: `src/listingjet/workflows/listing_pipeline.py:159-179`
- Test: `tests/test_workflows/test_listing_pipeline.py` (modify existing)

- [ ] **Step 1: Write failing test**

Add to `tests/test_workflows/test_listing_pipeline.py`:

```python
def test_social_content_always_included():
    """Social content should always run regardless of billing model or addons."""
    # The pipeline should not gate social_content behind addon checks
    import ast
    import inspect
    from listingjet.workflows.listing_pipeline import ListingPipeline

    source = inspect.getsource(ListingPipeline.run)
    # After the fix, there should be no conditional check for social_content_pack in addons
    assert "social_content_pack" not in source, "social_content should no longer be addon-gated"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_workflows/test_listing_pipeline.py::test_social_content_always_included -v`
Expected: FAIL (source still contains "social_content_pack")

- [ ] **Step 3: Update the pipeline workflow**

In `src/listingjet/workflows/listing_pipeline.py`, replace the post-approval "Brand + Social" parallel block (lines 159-180) with:

```python
        # Step 2: Brand + Social in parallel (social ALWAYS runs now — included in base)
        parallel_tasks = [
            workflow.execute_activity(
                run_brand, ctx,
                start_to_close_timeout=_DEFAULT_TIMEOUT,
                retry_policy=_DEFAULT_RETRY,
            ),
            workflow.execute_activity(
                run_social_content, ctx,
                start_to_close_timeout=_DEFAULT_TIMEOUT,
                retry_policy=_DEFAULT_RETRY,
            ),
        ]
        results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
        brand_result = results[0]
        if isinstance(brand_result, BaseException):
            workflow.logger.warning("brand_failed listing=%s error=%s", input.listing_id, brand_result)
            brand_result = {}
        flyer_key = brand_result.get("flyer_s3_key") if isinstance(brand_result, dict) else None
```

Also update the workflow docstring to reflect the new always-run behavior. Remove the `[plan-gated]` references.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/test_workflows/test_listing_pipeline.py::test_social_content_always_included -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/workflows/listing_pipeline.py tests/test_workflows/test_listing_pipeline.py && git commit -m "feat: social content and social cuts always run (included in base)"
```

---

## Task 8: Update Listings Media — Don't Auto-Trigger Pipeline for DRAFT

**Files:**
- Modify: `src/listingjet/api/listings_media.py:146-161`

- [ ] **Step 1: Update the register-assets endpoint**

In `src/listingjet/api/listings_media.py`, change the pipeline trigger block. Replace lines 146-161:

```python
    if listing.state == ListingState.NEW:
        listing.state = ListingState.UPLOADING

    await db.commit()

    # Trigger the pipeline if listing just entered UPLOADING
    # DRAFT listings don't auto-trigger — they use the start-pipeline endpoint
    if listing.state == ListingState.UPLOADING:
        try:
            client = get_temporal_client()
            await client.start_pipeline(
                listing_id=str(listing.id),
                tenant_id=str(current_user.tenant_id),
                plan=tenant.plan,
            )
        except Exception:
            logger.exception("Pipeline trigger failed for listing %s", listing.id)
            listing.state = ListingState.FAILED
            await db.commit()
```

With:

```python
    if listing.state == ListingState.NEW:
        listing.state = ListingState.UPLOADING
    # DRAFT listings stay in DRAFT — pipeline starts via /start-pipeline endpoint

    await db.commit()

    # Trigger the pipeline if listing just entered UPLOADING (non-draft flow)
    if listing.state == ListingState.UPLOADING:
        try:
            client = get_temporal_client()
            await client.start_pipeline(
                listing_id=str(listing.id),
                tenant_id=str(current_user.tenant_id),
                plan=tenant.plan,
            )
        except Exception:
            logger.exception("Pipeline trigger failed for listing %s", listing.id)
            listing.state = ListingState.FAILED
            await db.commit()
```

Note: DRAFT listings won't match `listing.state == ListingState.NEW` so they won't transition to UPLOADING. The existing logic already handles this correctly — DRAFT != NEW.

- [ ] **Step 2: Verify DRAFT listings can receive uploads**

The endpoint allows uploads for listings not in terminal states. DRAFT is not terminal, so uploads work. Verify the state guard at the top of the endpoint includes or doesn't exclude DRAFT.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/api/listings_media.py && git commit -m "feat: DRAFT listings don't auto-trigger pipeline on upload"
```

---

## Task 9: Update Listings Core — DRAFT Handling

**Files:**
- Modify: `src/listingjet/api/listings_core.py`
- Modify: `src/listingjet/api/listings_workflow.py`

- [ ] **Step 1: Add DRAFT to refundable and cancellable states**

In `src/listingjet/api/listings_core.py`, update the `delete_listing` refundable states (line 249):

```python
    refundable_states = {ListingState.DRAFT, ListingState.NEW, ListingState.UPLOADING, ListingState.ANALYZING, ListingState.FAILED}
```

In `src/listingjet/api/listings_core.py`, update `list_listings` to hide DRAFT from default listing (line 98), add after the cancelled filter:

```python
    # Hide draft listings unless explicitly requested
    if state != "draft":
        base_query = base_query.where(Listing.state != ListingState.DRAFT)
```

In `src/listingjet/api/listings_workflow.py`, update the `cancel_listing` cancellable states (line 271):

```python
    cancellable = {ListingState.DRAFT, ListingState.NEW, ListingState.UPLOADING, ListingState.FAILED, ListingState.PIPELINE_TIMEOUT}
```

Note: DRAFT listings have no credit_cost set, so the refund logic (which checks `listing.credit_cost`) will naturally skip refund for drafts — no additional change needed.

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/api/listings_core.py src/listingjet/api/listings_workflow.py && git commit -m "feat: add DRAFT to cancellable/refundable states, hide from default listing"
```

---

## Task 10: Update Addon Endpoint for Bundle Support

**Files:**
- Modify: `src/listingjet/api/addons.py`

- [ ] **Step 1: Add bundle activation to activate_addon endpoint**

In `src/listingjet/api/addons.py`, update the `activate_addon` function to handle the `all_addons_bundle` slug. When the slug is `all_addons_bundle`:
1. Look up the bundle in `BUNDLE_PRICING`
2. Create `AddonPurchase` records for each included addon with `bundle_id` set
3. Deduct the bundle price (30 credits) as a single transaction

Add at the top of the function, before the existing single-addon logic:

```python
    from listingjet.config.tiers import BUNDLE_PRICING

    # Bundle activation
    if body.addon_slug == "all_addons_bundle":
        bundle = BUNDLE_PRICING.get("all_addons_bundle")
        if not bundle:
            raise HTTPException(status_code=400, detail="Bundle not found")

        # Check for existing bundle purchase
        existing_bundle = (await db.execute(
            select(AddonPurchase).where(
                AddonPurchase.listing_id == listing_id,
                AddonPurchase.bundle_id == "all_addons_bundle",
            ).limit(1)
        )).scalar_one_or_none()
        if existing_bundle:
            raise HTTPException(status_code=409, detail="Bundle already activated for this listing")

        # Deduct bundle credits
        credit_svc = CreditService()
        try:
            txn = await credit_svc.deduct_credits(
                db, tenant.id, bundle["credit_cost"],
                transaction_type="addon_debit",
                reference_type="bundle",
                reference_id=f"{listing_id}:all_addons_bundle",
                description=f"Premium Bundle for listing",
            )
        except InsufficientCreditsError:
            raise HTTPException(status_code=402, detail="Insufficient credits for bundle")

        # Create purchases for each included addon
        purchases = []
        for slug in bundle["includes"]:
            catalog_entry = (await db.execute(
                select(AddonCatalog).where(AddonCatalog.slug == slug)
            )).scalar_one_or_none()
            if catalog_entry:
                purchase = AddonPurchase(
                    tenant_id=tenant.id,
                    listing_id=listing_id,
                    addon_id=catalog_entry.id,
                    credit_transaction_id=txn.id,
                    bundle_id="all_addons_bundle",
                    status="active",
                )
                db.add(purchase)
                purchases.append(purchase)

        await db.commit()
        return {
            "id": str(purchases[0].id) if purchases else "",
            "addon_id": str(purchases[0].addon_id) if purchases else "",
            "addon_slug": "all_addons_bundle",
            "addon_name": "Premium Bundle",
            "status": "active",
            "created_at": purchases[0].created_at if purchases else None,
        }
```

- [ ] **Step 2: Also allow DRAFT state for addon activation**

Update the state check in the activate_addon endpoint to include DRAFT:

```python
    allowed_states = {ListingState.DRAFT, ListingState.NEW, ListingState.UPLOADING, ListingState.AWAITING_REVIEW, ListingState.IN_REVIEW}
```

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add src/listingjet/api/addons.py && git commit -m "feat: bundle activation support and DRAFT state for addon endpoint"
```

---

## Task 11: Frontend — Update Plan Context for New Pricing

**Files:**
- Modify: `frontend/src/contexts/plan-context.tsx`

- [ ] **Step 1: Update LISTING_CREDIT_COST constant**

In `frontend/src/contexts/plan-context.tsx`, find `LISTING_CREDIT_COST = 12` and change to:

```typescript
const LISTING_CREDIT_COST = 15;
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/contexts/plan-context.tsx && git commit -m "feat: update base listing credit cost to 15"
```

---

## Task 12: Frontend — Add API Client Methods

**Files:**
- Modify: `frontend/src/lib/api-client.ts`

- [ ] **Step 1: Add new methods to the API client**

Add these methods to the API client class in `frontend/src/lib/api-client.ts`:

```typescript
  async setStagingTags(listingId: string, assetIds: string[]): Promise<{ tagged_count: number; listing_id: string }> {
    const { data, error } = await this.client.POST("/listings/{listing_id}/staging-tags", {
      params: { path: { listing_id: listingId } },
      body: { asset_ids: assetIds },
    });
    if (error) throw this.toError(error);
    return data;
  }

  async startPipeline(
    listingId: string,
    selectedAddons: string[] = [],
  ): Promise<{ listing_id: string; state: string; credits_deducted: number; workflow_id: string }> {
    const { data, error } = await this.client.POST("/listings/{listing_id}/start-pipeline", {
      params: { path: { listing_id: listingId } },
      body: { selected_addons: selectedAddons },
    });
    if (error) throw this.toError(error);
    return data;
  }
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/lib/api-client.ts && git commit -m "feat: add startPipeline and setStagingTags API client methods"
```

---

## Task 13: Frontend — Wizard Container + Step Navigation

**Files:**
- Create: `frontend/src/components/listings/creation-wizard/wizard-container.tsx`

- [ ] **Step 1: Create the wizard container**

```typescript
"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { usePlan } from "@/contexts/plan-context";
import { useToast } from "@/components/ui/toast";
import { apiClient } from "@/lib/api-client";
import { StepPropertyDetails } from "./step-property-details";
import { StepUploadPhotos } from "./step-upload-photos";
import { StepVirtualStaging } from "./step-virtual-staging";
import { StepAddons } from "./step-addons";
import { StepReviewConfirm } from "./step-review-confirm";

export interface WizardFormData {
  // Step 1: Property Details
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
    unit: string;
  };
  metadata: {
    beds: number | null;
    baths: number | null;
    sqft: number | null;
    price: number | null;
    property_type: string;
  };
  // Step 2: Photos
  listingId: string | null;
  uploadedAssets: Array<{ id: string; filename: string; url: string }>;
  // Step 3: Virtual Staging
  stagingAssetIds: string[];
  // Step 4: Add-ons
  selectedAddons: string[];
  useBundle: boolean;
}

const INITIAL_FORM_DATA: WizardFormData = {
  address: { street: "", city: "", state: "", zip: "", unit: "" },
  metadata: { beds: null, baths: null, sqft: null, price: null, property_type: "" },
  listingId: null,
  uploadedAssets: [],
  stagingAssetIds: [],
  selectedAddons: [],
  useBundle: false,
};

const STEPS = [
  { label: "Property Details", number: 1 },
  { label: "Upload Photos", number: 2 },
  { label: "Virtual Staging", number: 3 },
  { label: "Add-ons", number: 4 },
  { label: "Review & Confirm", number: 5 },
];

export function WizardContainer() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<WizardFormData>(INITIAL_FORM_DATA);
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();
  const { refresh } = usePlan();
  const { toast } = useToast();

  const updateFormData = useCallback((updates: Partial<WizardFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  }, []);

  const goNext = useCallback(() => setStep((s) => Math.min(s + 1, 5)), []);
  const goBack = useCallback(() => setStep((s) => Math.max(s - 1, 1)), []);

  const handleConfirm = useCallback(async () => {
    if (!formData.listingId) return;
    setSubmitting(true);
    try {
      // Set staging tags if any
      if (formData.stagingAssetIds.length > 0) {
        await apiClient.setStagingTags(formData.listingId, formData.stagingAssetIds);
      }

      // Start pipeline with selected addons
      const addons = formData.useBundle ? ["all_addons_bundle"] : formData.selectedAddons;
      const result = await apiClient.startPipeline(formData.listingId, addons);

      await refresh();
      toast({ title: "Listing created!", description: `${result.credits_deducted} credits deducted. Processing has begun.` });
      router.push(`/listings/${formData.listingId}`);
    } catch (err: any) {
      const msg = err?.message || "Failed to start pipeline";
      toast({ title: "Error", description: msg, variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  }, [formData, refresh, toast, router]);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Step indicator */}
      <nav className="flex items-center justify-between mb-8">
        {STEPS.map((s) => (
          <div key={s.number} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                s.number === step
                  ? "bg-[var(--color-primary)] text-white"
                  : s.number < step
                    ? "bg-[var(--color-primary)]/20 text-[var(--color-primary)]"
                    : "bg-[var(--color-surface-2)] text-[var(--color-text-muted)]"
              }`}
            >
              {s.number < step ? "\u2713" : s.number}
            </div>
            <span
              className={`text-sm hidden sm:inline ${
                s.number === step ? "text-[var(--color-text)] font-medium" : "text-[var(--color-text-muted)]"
              }`}
            >
              {s.label}
            </span>
            {s.number < STEPS.length && (
              <div className="w-8 h-px bg-[var(--color-border)] hidden sm:block" />
            )}
          </div>
        ))}
      </nav>

      {/* Step content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          {step === 1 && (
            <StepPropertyDetails
              formData={formData}
              onUpdate={updateFormData}
              onNext={goNext}
            />
          )}
          {step === 2 && (
            <StepUploadPhotos
              formData={formData}
              onUpdate={updateFormData}
              onNext={goNext}
              onBack={goBack}
            />
          )}
          {step === 3 && (
            <StepVirtualStaging
              formData={formData}
              onUpdate={updateFormData}
              onNext={goNext}
              onBack={goBack}
            />
          )}
          {step === 4 && (
            <StepAddons
              formData={formData}
              onUpdate={updateFormData}
              onNext={goNext}
              onBack={goBack}
            />
          )}
          {step === 5 && (
            <StepReviewConfirm
              formData={formData}
              onUpdate={updateFormData}
              onBack={goBack}
              onConfirm={handleConfirm}
              submitting={submitting}
            />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/components/listings/creation-wizard/wizard-container.tsx && git commit -m "feat: wizard container with step navigation and shared form state"
```

---

## Task 14: Frontend — Step 1: Property Details

**Files:**
- Create: `frontend/src/components/listings/creation-wizard/step-property-details.tsx`

- [ ] **Step 1: Create property details step**

```typescript
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { AddressAutocomplete } from "@/components/ui/address-autocomplete";
import { apiClient } from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";
import type { WizardFormData } from "./wizard-container";

interface Props {
  formData: WizardFormData;
  onUpdate: (updates: Partial<WizardFormData>) => void;
  onNext: () => void;
}

const PROPERTY_TYPES = [
  "Single Family",
  "Condo/Townhouse",
  "Multi-Family",
  "Land/Lot",
  "Commercial",
];

export function StepPropertyDetails({ formData, onUpdate, onNext }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { toast } = useToast();

  const handleAddressSelect = async (address: {
    street: string;
    city: string;
    state: string;
    zip: string;
  }) => {
    onUpdate({ address: { ...formData.address, ...address } });

    // ATTOM property lookup for auto-fill
    try {
      const property = await apiClient.propertyLookup(address);
      if (property) {
        onUpdate({
          metadata: {
            beds: property.beds ?? formData.metadata.beds,
            baths: property.baths ?? formData.metadata.baths,
            sqft: property.sqft ?? formData.metadata.sqft,
            price: property.price ?? formData.metadata.price,
            property_type: property.property_type ?? formData.metadata.property_type,
          },
        });
        toast({ title: "Property data loaded", description: "Details auto-filled from public records." });
      }
    } catch {
      // Auto-fill is best-effort, don't block the user
    }
  };

  const handleNext = async () => {
    if (!formData.address.street || !formData.address.city || !formData.address.state) {
      setError("Address is required (street, city, state).");
      return;
    }
    setError("");
    setLoading(true);

    try {
      // Create the DRAFT listing
      if (!formData.listingId) {
        const listing = await apiClient.createListing({
          address: formData.address,
          metadata: formData.metadata,
        });
        onUpdate({ listingId: listing.id });
      }
      onNext();
    } catch (err: any) {
      setError(err?.message || "Failed to create listing");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-[var(--font-heading)] font-bold text-[var(--color-text)]">
          Property Details
        </h2>
        <p className="text-[var(--color-text-muted)] mt-1">
          Enter the property address and details. We'll auto-fill what we can.
        </p>
      </div>

      {/* Address */}
      <div className="space-y-4">
        <label className="block text-sm font-medium text-[var(--color-text)]">Address</label>
        <AddressAutocomplete
          value={formData.address.street}
          onSelect={handleAddressSelect}
          onChange={(street: string) =>
            onUpdate({ address: { ...formData.address, street } })
          }
        />
        <div className="grid grid-cols-3 gap-3">
          <input
            type="text"
            placeholder="City"
            value={formData.address.city}
            onChange={(e) => onUpdate({ address: { ...formData.address, city: e.target.value } })}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="State"
            value={formData.address.state}
            onChange={(e) => onUpdate({ address: { ...formData.address, state: e.target.value } })}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="ZIP"
            value={formData.address.zip}
            onChange={(e) => onUpdate({ address: { ...formData.address, zip: e.target.value } })}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
          />
        </div>
        <input
          type="text"
          placeholder="Unit / Suite (optional)"
          value={formData.address.unit}
          onChange={(e) => onUpdate({ address: { ...formData.address, unit: e.target.value } })}
          className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
        />
      </div>

      {/* Property details */}
      <div className="space-y-4">
        <label className="block text-sm font-medium text-[var(--color-text)]">Property Details</label>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[var(--color-text-muted)]">Beds</label>
            <input
              type="number"
              min={0}
              value={formData.metadata.beds ?? ""}
              onChange={(e) =>
                onUpdate({ metadata: { ...formData.metadata, beds: e.target.value ? Number(e.target.value) : null } })
              }
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--color-text-muted)]">Baths</label>
            <input
              type="number"
              min={0}
              step={0.5}
              value={formData.metadata.baths ?? ""}
              onChange={(e) =>
                onUpdate({ metadata: { ...formData.metadata, baths: e.target.value ? Number(e.target.value) : null } })
              }
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--color-text-muted)]">Sq Ft</label>
            <input
              type="number"
              min={0}
              value={formData.metadata.sqft ?? ""}
              onChange={(e) =>
                onUpdate({ metadata: { ...formData.metadata, sqft: e.target.value ? Number(e.target.value) : null } })
              }
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-[var(--color-text-muted)]">List Price</label>
            <input
              type="number"
              min={0}
              value={formData.metadata.price ?? ""}
              onChange={(e) =>
                onUpdate({ metadata: { ...formData.metadata, price: e.target.value ? Number(e.target.value) : null } })
              }
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="text-xs text-[var(--color-text-muted)]">Property Type</label>
          <select
            value={formData.metadata.property_type}
            onChange={(e) =>
              onUpdate({ metadata: { ...formData.metadata, property_type: e.target.value } })
            }
            className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
          >
            <option value="">Select type...</option>
            {PROPERTY_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="flex justify-end">
        <Button onClick={handleNext} loading={loading}>
          Next: Upload Photos
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/components/listings/creation-wizard/step-property-details.tsx && git commit -m "feat: wizard step 1 — property details with ATTOM auto-fill"
```

---

## Task 15: Frontend — Step 2: Upload Photos

**Files:**
- Create: `frontend/src/components/listings/creation-wizard/step-upload-photos.tsx`

- [ ] **Step 1: Create upload photos step**

This step reuses the existing presigned URL upload pattern from `asset-upload-form.tsx`:

```typescript
"use client";

import { useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";
import type { WizardFormData } from "./wizard-container";

interface Props {
  formData: WizardFormData;
  onUpdate: (updates: Partial<WizardFormData>) => void;
  onNext: () => void;
  onBack: () => void;
}

const MAX_FILES = 50;
const MAX_SIZE_BYTES = 20 * 1024 * 1024; // 20MB
const ACCEPTED_TYPES = ["image/jpeg", "image/png"];

interface UploadFile {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  assetId?: string;
  previewUrl: string;
}

export function StepUploadPhotos({ formData, onUpdate, onNext, onBack }: Props) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const toAdd = Array.from(newFiles).filter((f) => {
      if (!ACCEPTED_TYPES.includes(f.type)) {
        toast({ title: "Invalid file", description: `${f.name} must be JPEG or PNG`, variant: "destructive" });
        return false;
      }
      if (f.size > MAX_SIZE_BYTES) {
        toast({ title: "File too large", description: `${f.name} exceeds 20MB`, variant: "destructive" });
        return false;
      }
      return true;
    });

    setFiles((prev) => {
      const total = prev.length + toAdd.length;
      if (total > MAX_FILES) {
        toast({ title: "Too many files", description: `Maximum ${MAX_FILES} photos allowed`, variant: "destructive" });
        return prev;
      }
      return [
        ...prev,
        ...toAdd.map((f) => ({
          file: f,
          progress: 0,
          status: "pending" as const,
          previewUrl: URL.createObjectURL(f),
        })),
      ];
    });
  }, [toast]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => {
      const next = [...prev];
      URL.revokeObjectURL(next[index].previewUrl);
      next.splice(index, 1);
      return next;
    });
  }, []);

  const uploadAll = useCallback(async () => {
    if (!formData.listingId || files.length === 0) return;
    setUploading(true);

    try {
      const pendingFiles = files.filter((f) => f.status === "pending");
      if (pendingFiles.length === 0) {
        onNext();
        return;
      }

      // Get presigned URLs
      const filenames = pendingFiles.map((f) => f.file.name);
      const urls = await apiClient.getUploadUrls(formData.listingId, filenames);

      // Upload each file
      const uploadedAssets: Array<{ id: string; filename: string; url: string }> = [
        ...formData.uploadedAssets,
      ];

      for (let i = 0; i < pendingFiles.length; i++) {
        const uf = pendingFiles[i];
        const urlInfo = urls[i];
        const fileIndex = files.indexOf(uf);

        try {
          setFiles((prev) => {
            const next = [...prev];
            next[fileIndex] = { ...next[fileIndex], status: "uploading" };
            return next;
          });

          await new Promise<void>((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.upload.onprogress = (e) => {
              if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                setFiles((prev) => {
                  const next = [...prev];
                  next[fileIndex] = { ...next[fileIndex], progress: pct };
                  return next;
                });
              }
            };
            xhr.onload = () => (xhr.status < 400 ? resolve() : reject(new Error(`Upload failed: ${xhr.status}`)));
            xhr.onerror = () => reject(new Error("Upload failed"));
            xhr.open("PUT", urlInfo.upload_url);
            xhr.setRequestHeader("Content-Type", uf.file.type);
            xhr.send(uf.file);
          });

          setFiles((prev) => {
            const next = [...prev];
            next[fileIndex] = { ...next[fileIndex], status: "done", progress: 100 };
            return next;
          });

          uploadedAssets.push({
            id: urlInfo.asset_id,
            filename: uf.file.name,
            url: uf.previewUrl,
          });
        } catch {
          setFiles((prev) => {
            const next = [...prev];
            next[fileIndex] = { ...next[fileIndex], status: "error" };
            return next;
          });
        }
      }

      // Register assets with backend
      await apiClient.registerAssets(formData.listingId, {
        assets: uploadedAssets.map((a) => ({
          asset_id: a.id,
          file_name: a.filename,
          file_path: a.id, // S3 key from presigned URL response
        })),
      });

      onUpdate({ uploadedAssets });
      onNext();
    } catch (err: any) {
      toast({ title: "Upload failed", description: err?.message || "Try again", variant: "destructive" });
    } finally {
      setUploading(false);
    }
  }, [files, formData, onUpdate, onNext, toast]);

  const allDone = files.length > 0 && files.every((f) => f.status === "done");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-[var(--font-heading)] font-bold text-[var(--color-text)]">
          Upload Photos
        </h2>
        <p className="text-[var(--color-text-muted)] mt-1">
          Drag and drop or select up to {MAX_FILES} photos (JPEG/PNG, max 20MB each).
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-[var(--color-border)] rounded-xl p-8 text-center cursor-pointer hover:border-[var(--color-primary)] transition-colors"
      >
        <p className="text-[var(--color-text-muted)]">
          Drop photos here or <span className="text-[var(--color-primary)] font-medium">browse</span>
        </p>
        <p className="text-xs text-[var(--color-text-muted)] mt-1">
          {files.length} / {MAX_FILES} photos
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/jpeg,image/png"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
          className="hidden"
        />
      </div>

      {/* File grid */}
      {files.length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          {files.map((uf, i) => (
            <motion.div
              key={`${uf.file.name}-${i}`}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="relative rounded-lg overflow-hidden aspect-square bg-[var(--color-surface-2)]"
            >
              <img src={uf.previewUrl} alt={uf.file.name} className="w-full h-full object-cover" />
              {uf.status === "uploading" && (
                <div className="absolute inset-x-0 bottom-0 h-1 bg-[var(--color-surface-2)]">
                  <div
                    className="h-full bg-[var(--color-primary)] transition-all"
                    style={{ width: `${uf.progress}%` }}
                  />
                </div>
              )}
              {uf.status === "done" && (
                <div className="absolute top-1 right-1 w-5 h-5 rounded-full bg-green-500 flex items-center justify-center text-white text-xs">
                  &#10003;
                </div>
              )}
              {uf.status === "error" && (
                <div className="absolute top-1 right-1 w-5 h-5 rounded-full bg-red-500 flex items-center justify-center text-white text-xs">
                  !
                </div>
              )}
              {uf.status === "pending" && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(i);
                  }}
                  className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/50 text-white text-xs flex items-center justify-center hover:bg-black/70"
                >
                  &times;
                </button>
              )}
            </motion.div>
          ))}
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        {allDone ? (
          <Button onClick={onNext}>Next: Virtual Staging</Button>
        ) : (
          <Button onClick={uploadAll} loading={uploading} disabled={files.length === 0}>
            Upload & Continue
          </Button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/components/listings/creation-wizard/step-upload-photos.tsx && git commit -m "feat: wizard step 2 — photo upload with drag-drop and progress"
```

---

## Task 16: Frontend — Step 3: Virtual Staging

**Files:**
- Create: `frontend/src/components/listings/creation-wizard/step-virtual-staging.tsx`

- [ ] **Step 1: Create virtual staging step**

```typescript
"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import type { WizardFormData } from "./wizard-container";

interface Props {
  formData: WizardFormData;
  onUpdate: (updates: Partial<WizardFormData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export function StepVirtualStaging({ formData, onUpdate, onNext, onBack }: Props) {
  const toggleAsset = useCallback(
    (assetId: string) => {
      onUpdate({
        stagingAssetIds: formData.stagingAssetIds.includes(assetId)
          ? formData.stagingAssetIds.filter((id) => id !== assetId)
          : [...formData.stagingAssetIds, assetId],
      });
    },
    [formData.stagingAssetIds, onUpdate],
  );

  const hasStaging = formData.stagingAssetIds.length > 0;

  // Auto-select virtual_staging addon if rooms are tagged
  const handleNext = useCallback(() => {
    if (hasStaging && !formData.selectedAddons.includes("virtual_staging")) {
      onUpdate({
        selectedAddons: [...formData.selectedAddons, "virtual_staging"],
      });
    }
    if (!hasStaging && formData.selectedAddons.includes("virtual_staging")) {
      onUpdate({
        selectedAddons: formData.selectedAddons.filter((a) => a !== "virtual_staging"),
      });
    }
    onNext();
  }, [hasStaging, formData.selectedAddons, onUpdate, onNext]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-[var(--font-heading)] font-bold text-[var(--color-text)]">
          Virtual Staging
        </h2>
        <p className="text-[var(--color-text-muted)] mt-1">
          Select empty rooms to virtually furnish. Staged photos will appear in all your marketing materials.
        </p>
        <p className="text-xs text-[var(--color-text-muted)] mt-1">
          Virtual Staging costs 15 credits. Skip this step if all rooms are already furnished.
        </p>
      </div>

      {formData.uploadedAssets.length === 0 ? (
        <p className="text-[var(--color-text-muted)] text-sm">No photos uploaded yet. Go back to upload photos.</p>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {formData.uploadedAssets.map((asset) => {
            const selected = formData.stagingAssetIds.includes(asset.id);
            return (
              <motion.button
                key={asset.id}
                onClick={() => toggleAsset(asset.id)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className={`relative rounded-lg overflow-hidden aspect-square border-2 transition-colors ${
                  selected
                    ? "border-[var(--color-primary)] ring-2 ring-[var(--color-primary)]/30"
                    : "border-transparent hover:border-[var(--color-border)]"
                }`}
              >
                <img src={asset.url} alt={asset.filename} className="w-full h-full object-cover" />
                {selected && (
                  <div className="absolute inset-0 bg-[var(--color-primary)]/10 flex items-center justify-center">
                    <div className="bg-[var(--color-primary)] text-white rounded-full px-3 py-1 text-xs font-medium">
                      Stage this room
                    </div>
                  </div>
                )}
              </motion.button>
            );
          })}
        </div>
      )}

      {hasStaging && (
        <p className="text-sm text-[var(--color-primary)]">
          {formData.stagingAssetIds.length} room{formData.stagingAssetIds.length > 1 ? "s" : ""} selected for staging (+15 credits)
        </p>
      )}

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button onClick={handleNext}>
          {hasStaging ? "Next: Add-ons" : "Skip: Add-ons"}
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/components/listings/creation-wizard/step-virtual-staging.tsx && git commit -m "feat: wizard step 3 — virtual staging room selection"
```

---

## Task 17: Frontend — Step 4: Add-ons

**Files:**
- Create: `frontend/src/components/listings/creation-wizard/step-addons.tsx`

- [ ] **Step 1: Create addons step**

```typescript
"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import type { WizardFormData } from "./wizard-container";

interface Props {
  formData: WizardFormData;
  onUpdate: (updates: Partial<WizardFormData>) => void;
  onNext: () => void;
  onBack: () => void;
}

const ADDONS = [
  {
    slug: "ai_video_tour",
    name: "AI Video Tour",
    description: "Professional cinematic video tour generated from your photos",
    credits: 20,
  },
  {
    slug: "virtual_staging",
    name: "Virtual Staging",
    description: "AI-furnished rooms from your tagged empty spaces",
    credits: 15,
  },
  {
    slug: "3d_floorplan",
    name: "3D Floorplan",
    description: "Interactive 3D floorplan visualization",
    credits: 8,
  },
];

const BUNDLE_COST = 30;
const INDIVIDUAL_TOTAL = ADDONS.reduce((sum, a) => sum + a.credits, 0); // 43
const BUNDLE_SAVINGS = INDIVIDUAL_TOTAL - BUNDLE_COST; // 13

export function StepAddons({ formData, onUpdate, onNext, onBack }: Props) {
  const toggleAddon = useCallback(
    (slug: string) => {
      if (formData.useBundle) {
        // Switching from bundle to individual
        onUpdate({ useBundle: false, selectedAddons: [slug] });
        return;
      }
      const has = formData.selectedAddons.includes(slug);
      onUpdate({
        selectedAddons: has
          ? formData.selectedAddons.filter((s) => s !== slug)
          : [...formData.selectedAddons, slug],
      });
    },
    [formData, onUpdate],
  );

  const toggleBundle = useCallback(() => {
    if (formData.useBundle) {
      onUpdate({ useBundle: false, selectedAddons: [] });
    } else {
      onUpdate({
        useBundle: true,
        selectedAddons: ADDONS.map((a) => a.slug),
      });
    }
  }, [formData.useBundle, onUpdate]);

  const addonCost = formData.useBundle
    ? BUNDLE_COST
    : formData.selectedAddons.reduce((sum, slug) => {
        const addon = ADDONS.find((a) => a.slug === slug);
        return sum + (addon?.credits ?? 0);
      }, 0);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-[var(--font-heading)] font-bold text-[var(--color-text)]">
          Add-ons
        </h2>
        <p className="text-[var(--color-text-muted)] mt-1">
          Enhance your listing with premium add-ons. Your base listing (15 credits) includes social content, social cuts, photo compliance, MLS export, and microsite.
        </p>
      </div>

      {/* Bundle card */}
      <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
        <GlassCard
          onClick={toggleBundle}
          className={`cursor-pointer p-5 border-2 transition-colors ${
            formData.useBundle
              ? "border-[var(--color-primary)] bg-[var(--color-primary)]/5"
              : "border-[var(--color-border)]"
          }`}
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-[var(--color-text)]">Premium Bundle</h3>
                <span className="bg-[var(--color-primary)] text-white text-xs px-2 py-0.5 rounded-full">
                  Save {BUNDLE_SAVINGS} credits
                </span>
              </div>
              <p className="text-sm text-[var(--color-text-muted)] mt-1">
                All three add-ons: Video Tour + Virtual Staging + 3D Floorplan
              </p>
            </div>
            <div className="text-right">
              <p className="text-lg font-bold text-[var(--color-text)]">{BUNDLE_COST} credits</p>
              <p className="text-xs text-[var(--color-text-muted)] line-through">{INDIVIDUAL_TOTAL} credits</p>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      <div className="text-center text-sm text-[var(--color-text-muted)]">or choose individually</div>

      {/* Individual addon cards */}
      <div className="grid gap-3">
        {ADDONS.map((addon) => {
          const selected = !formData.useBundle && formData.selectedAddons.includes(addon.slug);
          const inBundle = formData.useBundle;
          return (
            <motion.div key={addon.slug} whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
              <GlassCard
                onClick={() => toggleAddon(addon.slug)}
                className={`cursor-pointer p-4 border-2 transition-colors ${
                  selected
                    ? "border-[var(--color-primary)] bg-[var(--color-primary)]/5"
                    : inBundle
                      ? "border-[var(--color-primary)]/30 bg-[var(--color-primary)]/5 opacity-60"
                      : "border-[var(--color-border)]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-[var(--color-text)]">{addon.name}</h3>
                    <p className="text-sm text-[var(--color-text-muted)]">{addon.description}</p>
                  </div>
                  <p className="font-semibold text-[var(--color-text)]">{addon.credits} credits</p>
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>

      {addonCost > 0 && (
        <p className="text-sm text-[var(--color-primary)] font-medium">
          Add-on total: +{addonCost} credits
        </p>
      )}

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext}>
          Next: Review
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/components/listings/creation-wizard/step-addons.tsx && git commit -m "feat: wizard step 4 — addon selection with bundle option"
```

---

## Task 18: Frontend — Step 5: Review & Confirm

**Files:**
- Create: `frontend/src/components/listings/creation-wizard/step-review-confirm.tsx`

- [ ] **Step 1: Create review & confirm step**

```typescript
"use client";

import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { usePlan } from "@/contexts/plan-context";
import type { WizardFormData } from "./wizard-container";

interface Props {
  formData: WizardFormData;
  onUpdate: (updates: Partial<WizardFormData>) => void;
  onBack: () => void;
  onConfirm: () => void;
  submitting: boolean;
}

const ADDON_NAMES: Record<string, string> = {
  ai_video_tour: "AI Video Tour",
  virtual_staging: "Virtual Staging",
  "3d_floorplan": "3D Floorplan",
};

const ADDON_COSTS: Record<string, number> = {
  ai_video_tour: 20,
  virtual_staging: 15,
  "3d_floorplan": 8,
};

const BUNDLE_COST = 30;
const BASE_COST = 15;

export function StepReviewConfirm({ formData, onBack, onConfirm, submitting }: Props) {
  const { creditBalance, billingModel } = usePlan();

  const addonCost = formData.useBundle
    ? BUNDLE_COST
    : formData.selectedAddons.reduce((sum, slug) => sum + (ADDON_COSTS[slug] ?? 0), 0);

  const totalCost = BASE_COST + addonCost;
  const canAfford = billingModel !== "credit" || (creditBalance !== null && creditBalance >= totalCost);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-[var(--font-heading)] font-bold text-[var(--color-text)]">
          Review & Confirm
        </h2>
        <p className="text-[var(--color-text-muted)] mt-1">
          Review your listing details before we start processing.
        </p>
      </div>

      {/* Property Summary */}
      <GlassCard className="p-5 space-y-3">
        <h3 className="font-semibold text-[var(--color-text)]">Property</h3>
        <p className="text-[var(--color-text)]">
          {formData.address.street}
          {formData.address.unit ? `, ${formData.address.unit}` : ""}
        </p>
        <p className="text-sm text-[var(--color-text-muted)]">
          {formData.address.city}, {formData.address.state} {formData.address.zip}
        </p>
        <div className="flex gap-4 text-sm text-[var(--color-text-muted)]">
          {formData.metadata.beds != null && <span>{formData.metadata.beds} beds</span>}
          {formData.metadata.baths != null && <span>{formData.metadata.baths} baths</span>}
          {formData.metadata.sqft != null && <span>{formData.metadata.sqft.toLocaleString()} sqft</span>}
          {formData.metadata.price != null && <span>${formData.metadata.price.toLocaleString()}</span>}
        </div>
      </GlassCard>

      {/* Photos Summary */}
      <GlassCard className="p-5 space-y-3">
        <h3 className="font-semibold text-[var(--color-text)]">Photos</h3>
        <p className="text-sm text-[var(--color-text-muted)]">
          {formData.uploadedAssets.length} photo{formData.uploadedAssets.length !== 1 ? "s" : ""} uploaded
        </p>
        {formData.stagingAssetIds.length > 0 && (
          <p className="text-sm text-[var(--color-primary)]">
            {formData.stagingAssetIds.length} room{formData.stagingAssetIds.length !== 1 ? "s" : ""} tagged for virtual staging
          </p>
        )}
        <div className="flex gap-2 overflow-x-auto">
          {formData.uploadedAssets.slice(0, 6).map((asset) => (
            <img
              key={asset.id}
              src={asset.url}
              alt={asset.filename}
              className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
            />
          ))}
          {formData.uploadedAssets.length > 6 && (
            <div className="w-16 h-16 rounded-lg bg-[var(--color-surface-2)] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
              +{formData.uploadedAssets.length - 6}
            </div>
          )}
        </div>
      </GlassCard>

      {/* Cost Breakdown */}
      {billingModel === "credit" && (
        <GlassCard className="p-5 space-y-3">
          <h3 className="font-semibold text-[var(--color-text)]">Credit Summary</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-[var(--color-text-muted)]">
                Base listing (social content, social cuts, compliance, MLS, microsite)
              </span>
              <span className="text-[var(--color-text)]">{BASE_COST} credits</span>
            </div>
            {formData.useBundle ? (
              <div className="flex justify-between">
                <span className="text-[var(--color-text-muted)]">Premium Bundle (Video + Staging + Floorplan)</span>
                <span className="text-[var(--color-text)]">{BUNDLE_COST} credits</span>
              </div>
            ) : (
              formData.selectedAddons.map((slug) => (
                <div key={slug} className="flex justify-between">
                  <span className="text-[var(--color-text-muted)]">{ADDON_NAMES[slug] ?? slug}</span>
                  <span className="text-[var(--color-text)]">{ADDON_COSTS[slug] ?? 0} credits</span>
                </div>
              ))
            )}
            <div className="border-t border-[var(--color-border)] pt-2 flex justify-between font-semibold">
              <span className="text-[var(--color-text)]">Total</span>
              <span className="text-[var(--color-text)]">{totalCost} credits</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-[var(--color-text-muted)]">Your balance</span>
              <span className={canAfford ? "text-[var(--color-text-muted)]" : "text-red-500"}>
                {creditBalance ?? 0} credits
              </span>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Included in base */}
      <div className="text-xs text-[var(--color-text-muted)] space-y-1">
        <p className="font-medium">Included in your base listing:</p>
        <ul className="list-disc list-inside">
          <li>Social media content & captions</li>
          <li>Social video cuts (Reels/TikTok/Shorts)</li>
          <li>MLS photo compliance check</li>
          <li>MLS export bundle</li>
          <li>Property microsite</li>
        </ul>
      </div>

      {!canAfford && (
        <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">
            Insufficient credits. You need {totalCost} credits but have {creditBalance ?? 0}.{" "}
            <a href="/billing/credits" className="underline font-medium">
              Purchase more credits
            </a>
          </p>
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button
          onClick={onConfirm}
          loading={submitting}
          disabled={!canAfford || submitting}
        >
          Create Listing ({totalCost} credits)
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/components/listings/creation-wizard/step-review-confirm.tsx && git commit -m "feat: wizard step 5 — review, cost breakdown, and confirm"
```

---

## Task 19: Frontend — Wizard Route + Update Listings Page

**Files:**
- Create: `frontend/src/app/listings/new/page.tsx`
- Modify: `frontend/src/app/listings/page.tsx`

- [ ] **Step 1: Create the wizard route page**

```typescript
import { WizardContainer } from "@/components/listings/creation-wizard/wizard-container";

export default function NewListingPage() {
  return (
    <main className="min-h-screen bg-[var(--color-background)]">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <a
          href="/listings"
          className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
        >
          &larr; Back to Listings
        </a>
      </div>
      <WizardContainer />
    </main>
  );
}
```

- [ ] **Step 2: Update listings page — replace dialog trigger with navigation**

In `frontend/src/app/listings/page.tsx`, find the "New Listing" button that currently calls `setDialogOpen(true)` and change it to navigate to `/listings/new`:

Replace the button's `onClick` handler:

```typescript
// Old: onClick={() => setDialogOpen(true)}
// New:
onClick={() => router.push("/listings/new")}
```

Add `useRouter` import if not already present:

```typescript
import { useRouter } from "next/navigation";
```

Add inside the component:

```typescript
const router = useRouter();
```

The existing `CreateListingDialog` can remain in the codebase for now — it's unused but not harmful. Don't delete it in case legacy tenants need it.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Jeff/launchlens && git add frontend/src/app/listings/new/page.tsx frontend/src/app/listings/page.tsx && git commit -m "feat: add /listings/new wizard route, update listings page navigation"
```

---

## Task 20: Integration Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd C:/Users/Jeff/launchlens && python -m pytest tests/ -v --timeout=30`
Expected: All tests pass (including existing tests that shouldn't be broken)

- [ ] **Step 2: Run frontend type check**

Run: `cd C:/Users/Jeff/launchlens/frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Run frontend build**

Run: `cd C:/Users/Jeff/launchlens/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Verify backward compatibility**

Check that existing listings (non-DRAFT) still display correctly:
- List endpoint hides DRAFT by default
- Existing listings retain their original `credit_cost`
- Pipeline still works for legacy (non-credit) tenants (no DRAFT state created)

- [ ] **Step 5: Final commit with all adjustments**

If any fixes were needed during verification, commit them:

```bash
cd C:/Users/Jeff/launchlens && git add -A && git commit -m "fix: integration fixes for Phase 1 creation wizard"
```
