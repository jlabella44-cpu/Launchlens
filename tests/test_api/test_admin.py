# tests/test_api/test_admin.py
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register_admin(client: AsyncClient) -> tuple[str, str]:
    """Register an admin user, return (token, tenant_id)."""
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
    email = f"role-{uuid.uuid4()}@example.com"
    invite_resp = await async_client.post(f"/admin/tenants/{tenant_id}/users", json={
        "email": email, "password": "RolePass1!", "name": "Role User", "role": "operator",
    }, headers=_auth(token))
    user_id = invite_resp.json()["id"]
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


@pytest.mark.asyncio
async def test_platform_stats(async_client: AsyncClient):
    token, _ = await _register_admin(async_client)
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
