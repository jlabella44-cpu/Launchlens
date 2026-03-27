# Plan Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce tier-based limits so starter/pro/enterprise tenants are gated on listing count per month, assets per listing, and Vision Tier 2 access.

**Architecture:** A `PlanLimits` service defines per-tier limits as a code-level dict and exposes check functions. A `get_tenant` FastAPI dependency loads the full Tenant object for endpoints that need plan checks. The `create_listing` endpoint checks monthly listing quota, `register_assets` checks per-listing asset quota, and the VisionAgent Tier 2 activity skips when the tenant's plan doesn't include it. Limit violations return HTTP 403 with a clear upgrade message.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, pytest-asyncio

---

## File Structure

```
src/launchlens/
  services/plan_limits.py    CREATE  — PLAN_LIMITS dict, check_listing_quota, check_asset_quota
  api/deps.py                MODIFY  — add get_tenant dependency
  api/listings.py            MODIFY  — enforce limits on create_listing and register_assets
  activities/pipeline.py     MODIFY  — skip tier2 for plans without it

tests/test_api/
  test_plan_limits.py        CREATE  — unit + integration tests
```

---

## Plan Limits Definition

```python
PLAN_LIMITS = {
    "starter":    {"max_listings_per_month": 5,   "max_assets_per_listing": 25,  "tier2_vision": False},
    "pro":        {"max_listings_per_month": 50,  "max_assets_per_listing": 50,  "tier2_vision": True},
    "enterprise": {"max_listings_per_month": 500, "max_assets_per_listing": 100, "tier2_vision": True},
}
```

---

## Tasks

---

### Task 1: Plan limits service + get_tenant dep

**Files:**
- Create: `src/launchlens/services/plan_limits.py`
- Modify: `src/launchlens/api/deps.py`
- Create: `tests/test_api/test_plan_limits.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api/test_plan_limits.py`:

```python
# tests/test_api/test_plan_limits.py
import pytest
from launchlens.services.plan_limits import PLAN_LIMITS, get_limits


def test_plan_limits_has_all_tiers():
    assert "starter" in PLAN_LIMITS
    assert "pro" in PLAN_LIMITS
    assert "enterprise" in PLAN_LIMITS


def test_starter_limits():
    limits = get_limits("starter")
    assert limits["max_listings_per_month"] == 5
    assert limits["max_assets_per_listing"] == 25
    assert limits["tier2_vision"] is False


def test_pro_limits():
    limits = get_limits("pro")
    assert limits["max_listings_per_month"] == 50
    assert limits["max_assets_per_listing"] == 50
    assert limits["tier2_vision"] is True


def test_enterprise_limits():
    limits = get_limits("enterprise")
    assert limits["max_listings_per_month"] == 500
    assert limits["tier2_vision"] is True


def test_unknown_plan_returns_starter():
    """Unknown plan falls back to starter limits."""
    limits = get_limits("unknown")
    assert limits["max_listings_per_month"] == 5


def test_check_listing_quota_under_limit():
    from launchlens.services.plan_limits import check_listing_quota
    # Starter allows 5, current count is 3 → allowed
    assert check_listing_quota("starter", current_count=3) is True


def test_check_listing_quota_at_limit():
    from launchlens.services.plan_limits import check_listing_quota
    # Starter allows 5, current count is 5 → blocked
    assert check_listing_quota("starter", current_count=5) is False


def test_check_asset_quota_under_limit():
    from launchlens.services.plan_limits import check_asset_quota
    # Starter allows 25, adding 10 to existing 10 → allowed
    assert check_asset_quota("starter", existing_count=10, adding_count=10) is True


def test_check_asset_quota_over_limit():
    from launchlens.services.plan_limits import check_asset_quota
    # Starter allows 25, adding 20 to existing 10 → blocked (30 > 25)
    assert check_asset_quota("starter", existing_count=10, adding_count=20) is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_plan_limits.py -v 2>&1 | tail -15
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement plan limits service**

Create `src/launchlens/services/plan_limits.py`:

```python
PLAN_LIMITS: dict[str, dict] = {
    "starter": {
        "max_listings_per_month": 5,
        "max_assets_per_listing": 25,
        "tier2_vision": False,
    },
    "pro": {
        "max_listings_per_month": 50,
        "max_assets_per_listing": 50,
        "tier2_vision": True,
    },
    "enterprise": {
        "max_listings_per_month": 500,
        "max_assets_per_listing": 100,
        "tier2_vision": True,
    },
}


def get_limits(plan: str) -> dict:
    """Get limits for a plan tier. Falls back to starter for unknown plans."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])


def check_listing_quota(plan: str, current_count: int) -> bool:
    """Return True if tenant can create another listing this month."""
    return current_count < get_limits(plan)["max_listings_per_month"]


def check_asset_quota(plan: str, existing_count: int, adding_count: int) -> bool:
    """Return True if assets can be added without exceeding the per-listing limit."""
    return (existing_count + adding_count) <= get_limits(plan)["max_assets_per_listing"]
```

- [ ] **Step 4: Add get_tenant dependency**

Read `src/launchlens/api/deps.py` first. Add this dependency at the bottom (after `get_current_tenant`):

```python
from launchlens.models.tenant import Tenant


async def get_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Load the full Tenant object for the authenticated user."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
```

Add the import for `Tenant` at the top of the file.

- [ ] **Step 5: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_plan_limits.py -v 2>&1 | tail -15
```
Expected: All 9 PASS

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/services/plan_limits.py src/launchlens/api/deps.py tests/test_api/test_plan_limits.py && git commit -m "feat: add plan limits service and get_tenant dependency"
```

---

### Task 2: Enforce limits on create_listing and register_assets

**Files:**
- Modify: `src/launchlens/api/listings.py`
- Modify: `tests/test_api/test_plan_limits.py`

- [ ] **Step 1: Write failing integration tests**

Append to `tests/test_api/test_plan_limits.py`:

```python
import uuid
import jwt as pyjwt
from httpx import AsyncClient
from launchlens.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo"
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_listing_enforces_monthly_quota(async_client: AsyncClient):
    """Starter plan: 5 listings/month. 6th should return 403."""
    token, _ = await _register(async_client)
    for i in range(5):
        resp = await async_client.post("/listings", json={
            "address": {"street": f"{i} Quota St"}, "metadata": {},
        }, headers=_auth(token))
        assert resp.status_code == 201, f"Listing {i+1} should succeed"

    # 6th listing should be blocked
    resp = await async_client.post("/listings", json={
        "address": {"street": "6 Quota St"}, "metadata": {},
    }, headers=_auth(token))
    assert resp.status_code == 403
    assert "limit" in resp.json()["detail"].lower() or "upgrade" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_assets_enforces_per_listing_quota(async_client: AsyncClient):
    """Starter plan: 25 assets/listing. 26th should return 403."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Asset Quota St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    # Add 25 assets (at the limit)
    assets_batch = [{"file_path": f"s3://b/{i}.jpg", "file_hash": f"h{i:03d}"} for i in range(25)]
    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": assets_batch
    }, headers=_auth(token))
    assert resp.status_code == 201

    # Adding 1 more should be blocked
    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [{"file_path": "s3://b/extra.jpg", "file_hash": "hextra"}]
    }, headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_listing_allowed_under_quota(async_client: AsyncClient):
    """First listing for a new tenant should always succeed."""
    token, _ = await _register(async_client)
    resp = await async_client.post("/listings", json={
        "address": {"street": "OK St"}, "metadata": {},
    }, headers=_auth(token))
    assert resp.status_code == 201
```

- [ ] **Step 2: Run tests to verify integration tests fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_plan_limits.py -k "monthly_quota or per_listing_quota or allowed_under" -v 2>&1 | tail -15
```
Expected: FAIL — 201 instead of 403 (no enforcement yet) or ConnectionRefused

- [ ] **Step 3: Add enforcement to create_listing**

Read `src/launchlens/api/listings.py` first. Modify `create_listing`:

Add imports at top:
```python
from datetime import datetime, timezone
from sqlalchemy import func
from launchlens.models.tenant import Tenant
from launchlens.services.plan_limits import check_listing_quota, check_asset_quota
```

In the `create_listing` function, BEFORE creating the Listing object, add the quota check:

```python
    # Check monthly listing quota
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Count listings created this month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count(Listing.id)).where(
            Listing.tenant_id == current_user.tenant_id,
            Listing.created_at >= month_start,
        )
    )
    current_count = count_result.scalar() or 0

    if not check_listing_quota(tenant.plan, current_count):
        raise HTTPException(
            status_code=403,
            detail=f"Monthly listing limit reached ({current_count}). Upgrade your plan for more.",
        )
```

- [ ] **Step 4: Add enforcement to register_assets**

In the `register_assets` function, AFTER loading the listing and BEFORE the asset creation loop, add:

```python
    # Check per-listing asset quota
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing_count_result = await db.execute(
        select(func.count(Asset.id)).where(Asset.listing_id == listing.id)
    )
    existing_count = existing_count_result.scalar() or 0

    if not check_asset_quota(tenant.plan, existing_count, len(body.assets)):
        from launchlens.services.plan_limits import get_limits
        max_allowed = get_limits(tenant.plan)["max_assets_per_listing"]
        raise HTTPException(
            status_code=403,
            detail=f"Asset limit reached ({existing_count}/{max_allowed}). Upgrade your plan for more.",
        )
```

- [ ] **Step 5: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_plan_limits.py -v 2>&1 | tail -20
```
Expected: Unit tests PASS. Integration tests may fail with ConnectionRefused if DB is offline.

- [ ] **Step 6: Run full suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -15
```

- [ ] **Step 7: Commit and tag**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/listings.py tests/test_api/test_plan_limits.py && git commit -m "feat: enforce plan limits on listing and asset creation" && git tag v0.8.0-plan-enforcement && echo "Tagged v0.8.0-plan-enforcement"
```

---

## NOT in scope

- Vision Tier 2 gating in the activity (skip if plan doesn't include it) — deferred; all plans currently get Tier 2 during pipeline. Can gate later by reading tenant plan in the activity.
- Admin override to bypass limits — deferred
- Per-user limits (only per-tenant) — deferred
- Real-time usage dashboard — deferred
- Soft limits with warnings before hard block — deferred
- Rate limiting per minute (Redis rate limiter exists but not applied here) — deferred
- Configurable limits via admin API — limits are code-level for MVP

## What already exists

- `Tenant.plan` field with values "starter", "pro", "enterprise"
- `get_current_user` dependency returning User with `tenant_id`
- `create_listing` and `register_assets` endpoints in `listings.py`
- Stripe webhook updates `tenant.plan` on subscription changes
- `async_client` and `db_session` test fixtures
