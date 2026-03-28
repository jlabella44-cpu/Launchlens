# Admin Dashboard API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add admin API endpoints for managing tenants, users, and viewing platform-wide listing stats — so admins can manage the platform without direct database access.

**Architecture:** All admin endpoints live under `/admin` and require the `require_admin` dependency (role=ADMIN). Endpoints are organized into three groups: tenant management (list, update plan), user management (list users for a tenant, invite user, change role), and platform stats (listing counts by state, tenant summary). No new models — we query existing Tenant, User, and Listing tables.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Pydantic v2, pytest-asyncio

---

## File Structure

```
src/launchlens/api/
  schemas/admin.py           CREATE  — admin request/response schemas
  admin.py                   MODIFY  — add tenant, user, and stats endpoints
  deps.py                    MODIFY  — add get_db_admin (skips RLS)

tests/test_api/
  test_admin.py              CREATE  — admin endpoint tests
```

---

## Key Patterns

### Admin auth
Every endpoint uses `require_admin` which chains through `get_current_user` → checks `role == ADMIN`:
```python
@router.get("/tenants")
async def list_tenants(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
```

### RLS bypass for admin endpoints
RLS is enabled on all tenant-scoped tables (migration 001). `get_db` does `SET LOCAL app.current_tenant` which scopes queries to one tenant. Admin endpoints need cross-tenant access, so they use a new `get_db_admin` dependency that skips `SET LOCAL`:

```python
# In deps.py
async def get_db_admin():
    """DB session without tenant RLS — for admin cross-tenant queries."""
    async with AsyncSessionLocal() as session:
        yield session
```

Admin routes use `db: AsyncSession = Depends(get_db_admin)` instead of `get_db`.

### Test helper
Tests register an admin user via `/auth/register` (always creates ADMIN role), then extract tenant_id from the JWT to use in assertions. Tests use the admin's own tenant_id (from JWT payload) rather than relying on `tenants[0]` from list endpoints.

---

## Tasks

---

### Task 1: Admin schemas + get_db_admin + tenant management

**Files:**
- Modify: `src/launchlens/api/deps.py` (add `get_db_admin`)
- Create: `src/launchlens/api/schemas/admin.py`
- Modify: `src/launchlens/api/admin.py`
- Create: `tests/test_api/test_admin.py`

**IMPORTANT**: Before implementing admin routes, add `get_db_admin` to `deps.py` — a DB session that skips `SET LOCAL` so admin queries bypass RLS:

```python
# Add to src/launchlens/api/deps.py:
async def get_db_admin():
    """DB session without tenant RLS scope — for admin cross-tenant queries."""
    async with AsyncSessionLocal() as session:
        yield session
```

Add `from launchlens.database import AsyncSessionLocal` to the imports in `deps.py` if not already present.

All admin routes below use `db: AsyncSession = Depends(get_db_admin)` instead of `get_db`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_api/test_admin.py`:

```python
# tests/test_api/test_admin.py
import uuid
import pytest
from httpx import AsyncClient


async def _register_admin(client: AsyncClient) -> tuple[str, str]:
    """Register an admin user, return (token, tenant_id)."""
    import jwt as pyjwt
    from launchlens.config import settings
    email = f"admin-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "AdminPass1!", "name": "Admin", "company_name": "AdminCo"
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_tenants(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)
    resp = await async_client.get("/admin/tenants", headers=_auth(token))
    assert resp.status_code == 200
    tenants = resp.json()
    assert isinstance(tenants, list)
    assert any(t["id"] == tenant_id for t in tenants)


@pytest.mark.asyncio
async def test_list_tenants_requires_admin(async_client: AsyncClient):
    resp = await async_client.get("/admin/tenants")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_tenant(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)

    resp = await async_client.get(f"/admin/tenants/{tenant_id}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == tenant_id
    assert "name" in resp.json()
    assert "plan" in resp.json()
    assert "user_count" in resp.json()
    assert "listing_count" in resp.json()


@pytest.mark.asyncio
async def test_update_tenant_plan(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)

    resp = await async_client.patch(f"/admin/tenants/{tenant_id}", json={
        "plan": "pro"
    }, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["plan"] == "pro"


@pytest.mark.asyncio
async def test_update_tenant_name(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)

    resp = await async_client.patch(f"/admin/tenants/{tenant_id}", json={
        "name": "Renamed Corp"
    }, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Corp"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_admin.py -v 2>&1 | tail -15
```
Expected: FAIL — 404/405

- [ ] **Step 3: Create admin schemas**

Create `src/launchlens/api/schemas/admin.py`:

```python
import uuid
from datetime import datetime
from pydantic import BaseModel


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    plan: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantDetailResponse(TenantResponse):
    user_count: int
    listing_count: int


class UpdateTenantRequest(BaseModel):
    name: str | None = None
    plan: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    name: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_user(cls, user):
        return cls(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            name=user.name,
            role=user.role.value if hasattr(user.role, 'value') else user.role,
            created_at=user.created_at,
        )


class UpdateUserRoleRequest(BaseModel):
    role: str


class InviteUserRequest(BaseModel):
    email: str
    name: str | None = None
    password: str
    role: str = "operator"


class PlatformStatsResponse(BaseModel):
    total_tenants: int
    total_users: int
    total_listings: int
    listings_by_state: dict[str, int]
```

- [ ] **Step 4: Implement tenant endpoints**

Read `src/launchlens/api/admin.py` first. Replace entirely:

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from launchlens.api.deps import require_admin, get_db_admin
from launchlens.models.user import User
from launchlens.models.tenant import Tenant
from launchlens.models.listing import Listing
from launchlens.api.schemas.admin import (
    TenantResponse, TenantDetailResponse, UpdateTenantRequest,
)

router = APIRouter()


@router.get("/health-detail")
async def health_detail():
    return {"status": "ok", "detail": "admin"}


@router.get("/health")
async def admin_health(admin_user: User = Depends(require_admin)):
    return {"status": "ok", "role": admin_user.role.value}


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return result.scalars().all()


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user_count = (await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id)
    )).scalar() or 0

    listing_count = (await db.execute(
        select(func.count(Listing.id)).where(Listing.tenant_id == tenant_id)
    )).scalar() or 0

    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        stripe_customer_id=tenant.stripe_customer_id,
        stripe_subscription_id=tenant.stripe_subscription_id,
        created_at=tenant.created_at,
        user_count=user_count,
        listing_count=listing_count,
    )


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: UpdateTenantRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.name is not None:
        tenant.name = body.name
    if body.plan is not None:
        if body.plan not in ("starter", "pro", "enterprise"):
            raise HTTPException(status_code=400, detail="Invalid plan. Must be: starter, pro, enterprise")
        tenant.plan = body.plan

    await db.commit()
    await db.refresh(tenant)
    return tenant
```

- [ ] **Step 5: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_admin.py -v 2>&1 | tail -15
```
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/schemas/admin.py src/launchlens/api/admin.py tests/test_api/test_admin.py && git commit -m "feat: add admin tenant management endpoints (list, detail, update)"
```

---

### Task 2: User management endpoints

**Files:**
- Modify: `src/launchlens/api/admin.py`
- Modify: `tests/test_api/test_admin.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_api/test_admin.py`:

```python
@pytest.mark.asyncio
async def test_list_users_for_tenant(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)

    resp = await async_client.get(f"/admin/tenants/{tenant_id}/users", headers=_auth(token))
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 1
    assert users[0]["email"].endswith("@example.com")
    assert "role" in users[0]


@pytest.mark.asyncio
async def test_invite_user(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)

    invite_email = f"invited-{uuid.uuid4()}@example.com"
    resp = await async_client.post(f"/admin/tenants/{tenant_id}/users", json={
        "email": invite_email,
        "password": "InvitedPass1!",
        "name": "Invited User",
        "role": "operator",
    }, headers=_auth(token))
    assert resp.status_code == 201
    assert resp.json()["email"] == invite_email
    assert resp.json()["role"] == "operator"


@pytest.mark.asyncio
async def test_invite_duplicate_email_returns_409(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)

    email = f"dup-{uuid.uuid4()}@example.com"
    payload = {"email": email, "password": "DupPass1!", "name": "Dup", "role": "operator"}
    await async_client.post(f"/admin/tenants/{tenant_id}/users", json=payload, headers=_auth(token))
    resp = await async_client.post(f"/admin/tenants/{tenant_id}/users", json=payload, headers=_auth(token))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_change_user_role(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)

    # Invite a user first
    email = f"role-{uuid.uuid4()}@example.com"
    invite_resp = await async_client.post(f"/admin/tenants/{tenant_id}/users", json={
        "email": email, "password": "RolePass1!", "name": "Role User", "role": "operator",
    }, headers=_auth(token))
    user_id = invite_resp.json()["id"]

    # Change role to viewer
    resp = await async_client.patch(f"/admin/users/{user_id}/role", json={
        "role": "viewer"
    }, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"


@pytest.mark.asyncio
async def test_change_role_invalid_returns_400(async_client: AsyncClient):
    token, tenant_id = await _register_admin(async_client)

    email = f"bad-{uuid.uuid4()}@example.com"
    invite_resp = await async_client.post(f"/admin/tenants/{tenant_id}/users", json={
        "email": email, "password": "BadPass1!", "name": "Bad", "role": "operator",
    }, headers=_auth(token))
    user_id = invite_resp.json()["id"]

    resp = await async_client.patch(f"/admin/users/{user_id}/role", json={
        "role": "superadmin"
    }, headers=_auth(token))
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_admin.py -k "list_users or invite or change_role" -v 2>&1 | tail -15
```
Expected: FAIL — 404/405

- [ ] **Step 3: Add user management endpoints**

In `src/launchlens/api/admin.py`, add imports and routes. Add to the imports at top:

```python
from launchlens.services.auth import hash_password
from launchlens.models.user import User, UserRole
from launchlens.api.schemas.admin import (
    TenantResponse, TenantDetailResponse, UpdateTenantRequest,
    UserResponse, InviteUserRequest, UpdateUserRoleRequest,
)
```

Add these routes at the bottom:

```python
VALID_ROLES = {r.value for r in UserRole}


@router.get("/tenants/{tenant_id}/users", response_model=list[UserResponse])
async def list_users(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
    )
    return [UserResponse.from_orm_user(u) for u in result.scalars().all()]


@router.post("/tenants/{tenant_id}/users", status_code=201, response_model=UserResponse)
async def invite_user(
    tenant_id: uuid.UUID,
    body: InviteUserRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=UserRole(body.role),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.from_orm_user(user)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: uuid.UUID,
    body: UpdateUserRoleRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole(body.role)
    await db.commit()
    await db.refresh(user)
    return UserResponse.from_orm_user(user)
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_admin.py -v 2>&1 | tail -20
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/admin.py tests/test_api/test_admin.py && git commit -m "feat: add admin user management (list, invite, change role)"
```

---

### Task 3: Platform stats + tag

**Files:**
- Modify: `src/launchlens/api/admin.py`
- Modify: `tests/test_api/test_admin.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_api/test_admin.py`:

```python
@pytest.mark.asyncio
async def test_platform_stats(async_client: AsyncClient):
    token, _ = await _register_admin(async_client)
    # Create a listing so stats aren't empty
    await async_client.post("/listings", json={
        "address": {"street": "Stats St"}, "metadata": {},
    }, headers=_auth(token))

    resp = await async_client.get("/admin/stats", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_tenants"] >= 1
    assert body["total_users"] >= 1
    assert body["total_listings"] >= 1
    assert isinstance(body["listings_by_state"], dict)
    assert "new" in body["listings_by_state"]


@pytest.mark.asyncio
async def test_platform_stats_requires_admin(async_client: AsyncClient):
    resp = await async_client.get("/admin/stats")
    assert resp.status_code in (401, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_admin.py -k "stats" -v 2>&1 | tail -10
```
Expected: FAIL — 404/405

- [ ] **Step 3: Add stats endpoint**

In `src/launchlens/api/admin.py`, add import and route:

```python
from launchlens.api.schemas.admin import (
    TenantResponse, TenantDetailResponse, UpdateTenantRequest,
    UserResponse, InviteUserRequest, UpdateUserRoleRequest,
    PlatformStatsResponse,
)


@router.get("/stats", response_model=PlatformStatsResponse)
async def platform_stats(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    total_tenants = (await db.execute(select(func.count(Tenant.id)))).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_listings = (await db.execute(select(func.count(Listing.id)))).scalar() or 0

    # Listings grouped by state
    state_rows = (await db.execute(
        select(Listing.state, func.count(Listing.id)).group_by(Listing.state)
    )).all()
    listings_by_state = {
        row[0].value if hasattr(row[0], 'value') else row[0]: row[1]
        for row in state_rows
    }

    return PlatformStatsResponse(
        total_tenants=total_tenants,
        total_users=total_users,
        total_listings=total_listings,
        listings_by_state=listings_by_state,
    )
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest tests/test_api/test_admin.py -v 2>&1 | tail -20
```

- [ ] **Step 5: Run full suite**

```bash
cd /c/Users/Jeff/launchlens && PYTHON="/c/Users/Jeff/AppData/Local/Programs/Python/Python312/python.exe" && "$PYTHON" -m pytest --tb=short -q 2>&1 | tail -5
```

- [ ] **Step 6: Commit and tag**

```bash
cd /c/Users/Jeff/launchlens && git add src/launchlens/api/admin.py src/launchlens/api/schemas/admin.py tests/test_api/test_admin.py && git commit -m "feat: add admin platform stats endpoint" && git tag v0.8.2-admin-dashboard && echo "Tagged v0.8.2-admin-dashboard"
```

---

## NOT in scope

- Admin UI (frontend) — this is API-only; frontend is a separate plan
- Tenant deletion / deactivation — deferred (needs soft-delete pattern)
- User deletion — deferred
- Audit logging for admin actions — deferred
- Admin API rate limiting — deferred
- Pagination on list endpoints — MVP returns all
- Search/filter on tenants or users — deferred
- Super-admin role (above admin) — all admins are equal for MVP
- Cross-tenant user transfer — deferred

## What already exists

- `require_admin` dependency in `deps.py` — checks `role == ADMIN`
- `User` model with `UserRole` enum (admin, operator, agent, viewer)
- `Tenant` model with `plan`, `stripe_customer_id`, `stripe_subscription_id`
- `Listing` model with `state` enum
- Admin router at `/admin` with health check endpoints
- `hash_password` in `services/auth.py`
