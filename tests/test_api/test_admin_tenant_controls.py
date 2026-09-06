# tests/test_api/test_admin_tenant_controls.py
"""Admin controls on the Tenant model (migration 050):

- deactivated_at (soft-delete)
- bypass_limits (skip plan quotas)
- plan_overrides (per-tenant limit overrides)
"""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.config import settings
from listingjet.models.tenant import Tenant


async def _register(client: AsyncClient, plan_tier: str = "free") -> tuple[str, str]:
    email = f"tc-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo",
        "plan_tier": plan_tier,
    })
    assert resp.status_code in (200, 201), resp.text
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


async def _register_admin(client: AsyncClient) -> tuple[str, str]:
    from tests.conftest import promote_to_superadmin
    token, tenant_id = await _register(client)
    await promote_to_superadmin(client, token)
    return token, tenant_id


async def _set_legacy_billing(db: AsyncSession, tenant_id: str) -> None:
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
    )).scalar_one()
    tenant.billing_model = "legacy"
    await db.commit()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Admin endpoints ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deactivate_tenant_sets_timestamp(async_client: AsyncClient):
    admin_token, admin_tenant_id = await _register_admin(async_client)
    _, target_tenant = await _register(async_client)

    resp = await async_client.post(
        f"/admin/tenants/{target_tenant}/deactivate", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deactivated_at"] is not None
    assert body["id"] == target_tenant


@pytest.mark.asyncio
async def test_deactivate_tenant_is_idempotent(async_client: AsyncClient):
    admin_token, _ = await _register_admin(async_client)
    _, target_tenant = await _register(async_client)

    first = await async_client.post(
        f"/admin/tenants/{target_tenant}/deactivate", headers=_auth(admin_token)
    )
    first_ts = first.json()["deactivated_at"]

    second = await async_client.post(
        f"/admin/tenants/{target_tenant}/deactivate", headers=_auth(admin_token)
    )
    # idempotent — timestamp must not move on repeat calls
    assert second.status_code == 200
    assert second.json()["deactivated_at"] == first_ts


@pytest.mark.asyncio
async def test_activate_tenant_clears_timestamp(async_client: AsyncClient):
    admin_token, _ = await _register_admin(async_client)
    _, target_tenant = await _register(async_client)

    await async_client.post(
        f"/admin/tenants/{target_tenant}/deactivate", headers=_auth(admin_token)
    )
    resp = await async_client.post(
        f"/admin/tenants/{target_tenant}/activate", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    assert resp.json()["deactivated_at"] is None


@pytest.mark.asyncio
async def test_deactivated_tenant_blocks_auth(async_client: AsyncClient):
    """A tenant's users get 401 on authenticated endpoints once deactivated."""
    admin_token, _ = await _register_admin(async_client)
    user_token, target_tenant = await _register(async_client)

    # Sanity: user can hit /settings/usage before deactivation
    pre = await async_client.get("/settings/usage", headers=_auth(user_token))
    assert pre.status_code == 200

    await async_client.post(
        f"/admin/tenants/{target_tenant}/deactivate", headers=_auth(admin_token)
    )

    post = await async_client.get("/settings/usage", headers=_auth(user_token))
    assert post.status_code == 401


@pytest.mark.asyncio
async def test_list_tenants_excludes_deactivated_by_default(async_client: AsyncClient):
    admin_token, _ = await _register_admin(async_client)
    _, target_tenant = await _register(async_client)
    await async_client.post(
        f"/admin/tenants/{target_tenant}/deactivate", headers=_auth(admin_token)
    )

    resp = await async_client.get("/admin/tenants", headers=_auth(admin_token))
    assert resp.status_code == 200
    ids = {t["id"] for t in resp.json()["items"]}
    assert target_tenant not in ids

    resp = await async_client.get(
        "/admin/tenants?include_deactivated=true", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    ids = {t["id"] for t in resp.json()["items"]}
    assert target_tenant in ids


@pytest.mark.asyncio
async def test_set_bypass_limits_toggle(async_client: AsyncClient):
    admin_token, _ = await _register_admin(async_client)
    _, target_tenant = await _register(async_client)

    resp = await async_client.patch(
        f"/admin/tenants/{target_tenant}/bypass-limits",
        json={"enabled": True},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["bypass_limits"] is True

    resp = await async_client.patch(
        f"/admin/tenants/{target_tenant}/bypass-limits",
        json={"enabled": False},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["bypass_limits"] is False


@pytest.mark.asyncio
async def test_set_plan_overrides(async_client: AsyncClient):
    admin_token, _ = await _register_admin(async_client)
    _, target_tenant = await _register(async_client)

    resp = await async_client.patch(
        f"/admin/tenants/{target_tenant}/plan-overrides",
        json={"overrides": {"max_listings_per_month": 500}},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["plan_overrides"] == {"max_listings_per_month": 500}


@pytest.mark.asyncio
async def test_clear_plan_overrides_with_null(async_client: AsyncClient):
    admin_token, _ = await _register_admin(async_client)
    _, target_tenant = await _register(async_client)

    await async_client.patch(
        f"/admin/tenants/{target_tenant}/plan-overrides",
        json={"overrides": {"max_listings_per_month": 500}},
        headers=_auth(admin_token),
    )
    resp = await async_client.patch(
        f"/admin/tenants/{target_tenant}/plan-overrides",
        json={"overrides": None},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["plan_overrides"] is None


@pytest.mark.asyncio
async def test_admin_controls_require_superadmin(async_client: AsyncClient):
    token, tenant_id = await _register(async_client)  # not superadmin

    for resp in [
        await async_client.post(f"/admin/tenants/{tenant_id}/deactivate", headers=_auth(token)),
        await async_client.post(f"/admin/tenants/{tenant_id}/activate", headers=_auth(token)),
        await async_client.patch(
            f"/admin/tenants/{tenant_id}/bypass-limits",
            json={"enabled": True}, headers=_auth(token),
        ),
        await async_client.patch(
            f"/admin/tenants/{tenant_id}/plan-overrides",
            json={"overrides": {}}, headers=_auth(token),
        ),
    ]:
        assert resp.status_code == 403


# ── Quota integration ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bypass_limits_skips_monthly_listing_quota(
    async_client: AsyncClient, db_session: AsyncSession
):
    """With bypass_limits=True, free-plan tenants can exceed the 5/month cap."""
    admin_token, _ = await _register_admin(async_client)
    user_token, target_tenant = await _register(async_client)
    await _set_legacy_billing(db_session, target_tenant)

    # Enable bypass
    await async_client.patch(
        f"/admin/tenants/{target_tenant}/bypass-limits",
        json={"enabled": True},
        headers=_auth(admin_token),
    )

    # 7 listings on a free plan — would normally 403 at the 6th
    for i in range(7):
        resp = await async_client.post("/listings", json={
            "address": {"street": f"{i} Bypass St"}, "metadata": {},
        }, headers=_auth(user_token))
        assert resp.status_code == 201, f"listing {i+1} should bypass the quota"


@pytest.mark.asyncio
async def test_plan_overrides_raises_quota(
    async_client: AsyncClient, db_session: AsyncSession
):
    """A plan_override of max_listings_per_month raises the effective cap."""
    admin_token, _ = await _register_admin(async_client)
    user_token, target_tenant = await _register(async_client)
    await _set_legacy_billing(db_session, target_tenant)

    await async_client.patch(
        f"/admin/tenants/{target_tenant}/plan-overrides",
        json={"overrides": {"max_listings_per_month": 7}},
        headers=_auth(admin_token),
    )

    for i in range(7):
        resp = await async_client.post("/listings", json={
            "address": {"street": f"{i} Override St"}, "metadata": {},
        }, headers=_auth(user_token))
        assert resp.status_code == 201, f"listing {i+1} should fit within the override"

    resp = await async_client.post("/listings", json={
        "address": {"street": "8 Override St"}, "metadata": {},
    }, headers=_auth(user_token))
    assert resp.status_code == 403
