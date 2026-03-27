# tests/test_api/test_admin.py
import uuid
import pytest
import jwt as pyjwt
from httpx import AsyncClient
from launchlens.config import settings


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
