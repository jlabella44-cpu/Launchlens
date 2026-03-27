# API Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stub listing and asset endpoints with real CRUD operations so users can create listings, register assets, review AI-selected packages, and approve for delivery.

**Architecture:** All endpoints require JWT auth via `get_current_user`. Listings and assets are tenant-scoped — the tenant_id comes from the authenticated user, not from the request body. Listing state transitions follow the pipeline state machine: NEW → UPLOADING → (pipeline runs) → AWAITING_REVIEW → IN_REVIEW → APPROVED. The pipeline trigger is out of scope (Temporal wiring); these endpoints set the correct state for each user action.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Pydantic v2, pytest-asyncio, httpx AsyncClient

---

## File Structure

```
src/launchlens/api/
  schemas/
    listings.py          CREATE  — CreateListingRequest, UpdateListingRequest, ListingResponse, ListingDetailResponse
    assets.py            CREATE  — CreateAssetsRequest, AssetResponse
  listings.py            MODIFY  — replace stub with real CRUD + review + approve
  assets.py              MODIFY  — replace stub with real asset registration

tests/test_api/
  test_listings.py       CREATE  — listing endpoint tests
  test_assets.py         CREATE  — asset endpoint tests
```

---

## Key Patterns (read before implementing)

### Auth + tenant scoping
Every endpoint uses `get_current_user` to identify the caller. The user's `tenant_id` scopes all queries:
```python
from launchlens.api.deps import get_current_user
from launchlens.models.user import User

@router.post("")
async def create_listing(
    body: CreateListingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Use current_user.tenant_id for all DB writes
```

### Listing state machine (relevant states for API)
```
NEW → UPLOADING → [pipeline] → AWAITING_REVIEW → IN_REVIEW → APPROVED → [distribution] → DELIVERED
```
- `POST /listings` → creates in NEW
- `POST /listings/{id}/assets` → transitions to UPLOADING
- `POST /listings/{id}/review` → transitions to IN_REVIEW
- `POST /listings/{id}/approve` → transitions to APPROVED

### Tenant isolation
Queries MUST filter by `tenant_id` to prevent cross-tenant access:
```python
listing = (await db.execute(
    select(Listing).where(Listing.id == listing_id, Listing.tenant_id == current_user.tenant_id)
)).scalar_one_or_none()
if not listing:
    raise HTTPException(status_code=404)
```

### Test pattern
All API tests use `async_client` fixture (from `tests/conftest.py`) and register a user first to get a valid JWT. Use unique emails per test (`f"test-{uuid.uuid4()}@example.com"`).

### Helper: register and get token
Tests will repeatedly register + get a token. Define a helper in the test file:
```python
async def _register(client: AsyncClient) -> tuple[str, str]:
    """Register a user, return (token, tenant_id_from_jwt)."""
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo"
    })
    token = resp.json()["access_token"]
    # Decode to get tenant_id
    import jwt as pyjwt
    from launchlens.config import settings
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]
```

---

## Tasks

---

### Task 1: Listing schemas + POST/GET /listings

**Files:**
- Create: `src/launchlens/api/schemas/listings.py`
- Modify: `src/launchlens/api/listings.py`
- Create: `tests/test_api/test_listings.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api/test_listings.py`:

```python
# tests/test_api/test_listings.py
import uuid
import pytest
import jwt as pyjwt
from httpx import AsyncClient
from launchlens.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    """Register a user, return (token, tenant_id)."""
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
async def test_create_listing(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.post("/listings", json={
        "address": {"street": "100 Main St", "city": "Austin", "state": "TX", "zip": "78701"},
        "metadata": {"beds": 3, "baths": 2, "sqft": 1500, "price": 350000},
    }, headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["state"] == "new"
    assert body["address"]["city"] == "Austin"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_listings_empty(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.get("/listings", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_listings_returns_own(async_client: AsyncClient):
    token, _ = await _register(async_client)
    # Create a listing
    await async_client.post("/listings", json={
        "address": {"street": "1 A St"}, "metadata": {"beds": 1},
    }, headers=_auth(token))
    resp = await async_client.get("/listings", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_list_listings_tenant_isolation(async_client: AsyncClient):
    """Tenant A cannot see Tenant B's listings."""
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)
    # Create listing as Tenant A
    await async_client.post("/listings", json={
        "address": {"street": "A St"}, "metadata": {},
    }, headers=_auth(token_a))
    # Tenant B sees nothing
    resp = await async_client.get("/listings", headers=_auth(token_b))
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_listing_requires_auth(async_client: AsyncClient):
    resp = await async_client.post("/listings", json={"address": {}, "metadata": {}})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_listings.py -v 2>&1 | tail -20
```
Expected: FAIL (stubs return wrong responses)

- [ ] **Step 3: Create listing schemas**

Create `src/launchlens/api/schemas/listings.py`:

```python
import uuid
from datetime import datetime
from pydantic import BaseModel


class CreateListingRequest(BaseModel):
    address: dict
    metadata: dict = {}


class UpdateListingRequest(BaseModel):
    address: dict | None = None
    metadata: dict | None = None


class ListingResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    address: dict
    metadata: dict
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_listing(cls, listing):
        return cls(
            id=listing.id,
            tenant_id=listing.tenant_id,
            address=listing.address,
            metadata=listing.metadata_,
            state=listing.state.value if hasattr(listing.state, 'value') else listing.state,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
        )
```

- [ ] **Step 4: Implement listing CRUD**

Replace `src/launchlens/api/listings.py` entirely:

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from launchlens.database import get_db
from launchlens.models.listing import Listing, ListingState
from launchlens.models.user import User
from launchlens.api.deps import get_current_user
from launchlens.api.schemas.listings import (
    CreateListingRequest, ListingResponse,
)

router = APIRouter()


@router.post("", status_code=201, response_model=ListingResponse)
async def create_listing(
    body: CreateListingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = Listing(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        address=body.address,
        metadata_=body.metadata,
        state=ListingState.NEW,
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return ListingResponse.from_orm_listing(listing)


@router.get("", response_model=list[ListingResponse])
async def list_listings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Listing)
        .where(Listing.tenant_id == current_user.tenant_id)
        .order_by(Listing.created_at.desc())
    )
    listings = result.scalars().all()
    return [ListingResponse.from_orm_listing(l) for l in listings]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_listings.py -v 2>&1 | tail -20
```
Expected: All PASS (DB-dependent — may fail with ConnectionRefused if DB offline)

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/schemas/listings.py src/launchlens/api/listings.py tests/test_api/test_listings.py && git commit -m "feat: add POST/GET /listings with tenant scoping"
```

---

### Task 2: GET/PATCH /listings/{id}

**Files:**
- Modify: `src/launchlens/api/schemas/listings.py`
- Modify: `src/launchlens/api/listings.py`
- Modify: `tests/test_api/test_listings.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_api/test_listings.py`:

```python
@pytest.mark.asyncio
async def test_get_listing_detail(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "200 Oak Ln"}, "metadata": {"beds": 4},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == listing_id
    assert resp.json()["address"]["street"] == "200 Oak Ln"


@pytest.mark.asyncio
async def test_get_listing_not_found(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.get(f"/listings/{uuid.uuid4()}", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_listing_cross_tenant_404(async_client: AsyncClient):
    """Tenant B cannot see Tenant A's listing."""
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Secret St"}, "metadata": {},
    }, headers=_auth(token_a))
    listing_id = create_resp.json()["id"]
    resp = await async_client.get(f"/listings/{listing_id}", headers=_auth(token_b))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_listing(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Old St"}, "metadata": {"beds": 2},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.patch(f"/listings/{listing_id}", json={
        "address": {"street": "New St", "city": "Denver"},
    }, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["address"]["street"] == "New St"


@pytest.mark.asyncio
async def test_update_listing_metadata_only(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Keep St"}, "metadata": {"beds": 2},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.patch(f"/listings/{listing_id}", json={
        "metadata": {"beds": 3, "baths": 2},
    }, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["metadata"]["beds"] == 3
    # Address unchanged
    assert resp.json()["address"]["street"] == "Keep St"
```

- [ ] **Step 2: Run tests to verify new ones fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_listings.py -k "detail or not_found or cross_tenant or update" -v 2>&1 | tail -20
```
Expected: FAIL — 405 Method Not Allowed or 404

- [ ] **Step 3: Add GET/{id} and PATCH/{id} to listings router**

In `src/launchlens/api/listings.py`, add these routes. Import `UpdateListingRequest` from schemas:

```python
from launchlens.api.schemas.listings import (
    CreateListingRequest, UpdateListingRequest, ListingResponse,
)


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: uuid.UUID,
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
    return ListingResponse.from_orm_listing(listing)


@router.patch("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: uuid.UUID,
    body: UpdateListingRequest,
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

    if body.address is not None:
        listing.address = body.address
    if body.metadata is not None:
        listing.metadata_ = body.metadata

    await db.commit()
    await db.refresh(listing)
    return ListingResponse.from_orm_listing(listing)
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_listings.py -v 2>&1 | tail -25
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/listings.py src/launchlens/api/schemas/listings.py tests/test_api/test_listings.py && git commit -m "feat: add GET/PATCH /listings/{id} with tenant isolation"
```

---

### Task 3: Asset registration (POST/GET /listings/{id}/assets)

**Files:**
- Create: `src/launchlens/api/schemas/assets.py`
- Modify: `src/launchlens/api/assets.py`
- Modify: `src/launchlens/main.py`
- Create: `tests/test_api/test_assets.py`

The asset routes are nested under `/listings/{listing_id}/assets`. We'll mount them on the listings router rather than the separate assets router, since they're always listing-scoped. The existing `assets.py` stub router at `/assets` can remain for standalone asset lookup (Phase 2 API).

- [ ] **Step 1: Write failing tests**

Create `tests/test_api/test_assets.py`:

```python
# tests/test_api/test_assets.py
import uuid
import hashlib
import pytest
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
async def test_register_assets(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "1 Photo St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [
            {"file_path": "s3://bucket/photo1.jpg", "file_hash": "aaa111"},
            {"file_path": "s3://bucket/photo2.jpg", "file_hash": "bbb222"},
        ]
    }, headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["count"] == 2
    assert body["listing_state"] == "uploading"


@pytest.mark.asyncio
async def test_list_assets(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "2 Photo St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [{"file_path": "s3://bucket/a.jpg", "file_hash": "hash1"}]
    }, headers=_auth(token))

    resp = await async_client.get(f"/listings/{listing_id}/assets", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["file_path"] == "s3://bucket/a.jpg"
    assert resp.json()[0]["state"] == "uploaded"


@pytest.mark.asyncio
async def test_register_assets_wrong_tenant(async_client: AsyncClient):
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Private St"}, "metadata": {},
    }, headers=_auth(token_a))
    listing_id = create_resp.json()["id"]

    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [{"file_path": "s3://bucket/x.jpg", "file_hash": "xxx"}]
    }, headers=_auth(token_b))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_register_assets_requires_auth(async_client: AsyncClient):
    resp = await async_client.post(f"/listings/{uuid.uuid4()}/assets", json={
        "assets": [{"file_path": "s3://x.jpg", "file_hash": "x"}]
    })
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_assets.py -v 2>&1 | tail -20
```
Expected: FAIL — 404/405

- [ ] **Step 3: Create asset schemas**

Create `src/launchlens/api/schemas/assets.py`:

```python
import uuid
from datetime import datetime
from pydantic import BaseModel


class AssetInput(BaseModel):
    file_path: str
    file_hash: str


class CreateAssetsRequest(BaseModel):
    assets: list[AssetInput]


class CreateAssetsResponse(BaseModel):
    count: int
    listing_state: str


class AssetResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID | None
    file_path: str
    file_hash: str
    state: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Implement asset endpoints on listings router**

In `src/launchlens/api/listings.py`, add the nested asset routes. Add imports:

```python
from launchlens.models.asset import Asset
from launchlens.api.schemas.assets import (
    CreateAssetsRequest, CreateAssetsResponse, AssetResponse,
)


@router.post("/{listing_id}/assets", status_code=201, response_model=CreateAssetsResponse)
async def register_assets(
    listing_id: uuid.UUID,
    body: CreateAssetsRequest,
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

    for a in body.assets:
        asset = Asset(
            tenant_id=current_user.tenant_id,
            listing_id=listing.id,
            file_path=a.file_path,
            file_hash=a.file_hash,
            state="uploaded",
        )
        db.add(asset)

    # Transition listing to UPLOADING
    if listing.state == ListingState.NEW:
        listing.state = ListingState.UPLOADING

    await db.commit()
    return CreateAssetsResponse(
        count=len(body.assets),
        listing_state=listing.state.value,
    )


@router.get("/{listing_id}/assets", response_model=list[AssetResponse])
async def list_assets(
    listing_id: uuid.UUID,
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

    result = await db.execute(
        select(Asset).where(Asset.listing_id == listing.id).order_by(Asset.created_at)
    )
    return result.scalars().all()
```

- [ ] **Step 5: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_assets.py -v 2>&1 | tail -20
```
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/schemas/assets.py src/launchlens/api/listings.py tests/test_api/test_assets.py && git commit -m "feat: add POST/GET /listings/{id}/assets with tenant isolation"
```

---

### Task 4: Package review + approve

**Files:**
- Modify: `src/launchlens/api/listings.py`
- Modify: `tests/test_api/test_listings.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_api/test_listings.py`:

```python
from launchlens.models.listing import ListingState


@pytest.mark.asyncio
async def test_get_package_empty(async_client: AsyncClient):
    """GET /listings/{id}/package returns empty list when no selections exist."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Pkg St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}/package", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_start_review(async_client: AsyncClient, db_session):
    """POST /listings/{id}/review transitions from AWAITING_REVIEW to IN_REVIEW."""
    token, tenant_id = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Review St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    # Manually set state to AWAITING_REVIEW (simulates pipeline completion)
    from launchlens.models.listing import Listing
    from sqlalchemy import update
    await db_session.execute(
        update(Listing).where(Listing.id == uuid.UUID(listing_id)).values(state=ListingState.AWAITING_REVIEW)
    )
    await db_session.commit()

    resp = await async_client.post(f"/listings/{listing_id}/review", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["state"] == "in_review"


@pytest.mark.asyncio
async def test_approve_listing(async_client: AsyncClient, db_session):
    """POST /listings/{id}/approve transitions from IN_REVIEW to APPROVED."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Approve St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    # Manually set state to IN_REVIEW
    from launchlens.models.listing import Listing
    from sqlalchemy import update
    await db_session.execute(
        update(Listing).where(Listing.id == uuid.UUID(listing_id)).values(state=ListingState.IN_REVIEW)
    )
    await db_session.commit()

    resp = await async_client.post(f"/listings/{listing_id}/approve", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"


@pytest.mark.asyncio
async def test_approve_wrong_state_returns_409(async_client: AsyncClient):
    """Cannot approve a listing that is not IN_REVIEW."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Bad Approve St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    # Listing is in NEW state — cannot approve
    resp = await async_client.post(f"/listings/{listing_id}/approve", headers=_auth(token))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_review_wrong_state_returns_409(async_client: AsyncClient):
    """Cannot start review on a listing not in AWAITING_REVIEW."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Bad Review St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    # Listing is in NEW state — cannot review
    resp = await async_client.post(f"/listings/{listing_id}/review", headers=_auth(token))
    assert resp.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_listings.py -k "package or review or approve" -v 2>&1 | tail -20
```
Expected: FAIL — 405/404

- [ ] **Step 3: Add package, review, approve routes**

In `src/launchlens/api/listings.py`, add imports and routes:

```python
from launchlens.models.package_selection import PackageSelection


@router.get("/{listing_id}/package")
async def get_package(
    listing_id: uuid.UUID,
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

    result = await db.execute(
        select(PackageSelection)
        .where(PackageSelection.listing_id == listing.id)
        .order_by(PackageSelection.position)
    )
    selections = result.scalars().all()
    return [
        {
            "asset_id": str(s.asset_id),
            "channel": s.channel,
            "position": s.position,
            "composite_score": s.composite_score,
            "selected_by": s.selected_by,
        }
        for s in selections
    ]


@router.post("/{listing_id}/review")
async def start_review(
    listing_id: uuid.UUID,
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

    if listing.state != ListingState.AWAITING_REVIEW:
        raise HTTPException(status_code=409, detail=f"Cannot start review: listing is {listing.state.value}")

    listing.state = ListingState.IN_REVIEW
    await db.commit()
    await db.refresh(listing)
    return {"listing_id": str(listing.id), "state": listing.state.value}


@router.post("/{listing_id}/approve")
async def approve_listing(
    listing_id: uuid.UUID,
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

    if listing.state != ListingState.IN_REVIEW:
        raise HTTPException(status_code=409, detail=f"Cannot approve: listing is {listing.state.value}")

    listing.state = ListingState.APPROVED
    await db.commit()
    await db.refresh(listing)
    return {"listing_id": str(listing.id), "state": listing.state.value}
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_listings.py -v 2>&1 | tail -30
```
Expected: All PASS

- [ ] **Step 5: Run full test suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -15
```

- [ ] **Step 6: Commit and tag**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/listings.py tests/test_api/test_listings.py && git commit -m "feat: add package review, start review, approve endpoints" && git tag v0.6.0-api-endpoints && echo "Tagged v0.6.0-api-endpoints"
```

---

## NOT in scope

- File upload (S3 presigned URL generation) — assets are registered by path/hash; actual upload handled client-side
- Temporal pipeline trigger from asset registration — the UPLOADING state is set; Temporal watches for it
- Pagination on list endpoints — MVP returns all results
- Listing deletion — deferred (soft delete pattern)
- Asset deletion or replacement — deferred
- Package selection editing (drag-and-drop reorder) — deferred to frontend plan
- Webhook to notify client of pipeline completion — deferred

## What already exists

- `Listing` model with full state machine (`ListingState` enum)
- `Asset` model with `listing_id`, `file_path`, `file_hash`, `state`
- `PackageSelection` model with `listing_id`, `asset_id`, `position`, `composite_score`, `channel`
- `get_current_user` dependency — JWT auth
- `get_db` dependency with RLS via `SET LOCAL app.current_tenant`
- `TenantMiddleware` — sets `request.state.tenant_id` from JWT
- Auth schemas pattern in `api/schemas/auth.py`
- `async_client` and `db_session` fixtures in `tests/conftest.py`
