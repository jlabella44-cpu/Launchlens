# tests/test_middleware/test_tenant.py
import pytest
from httpx import AsyncClient
from launchlens.main import app


@pytest.mark.asyncio
async def test_request_without_auth_returns_401(async_client):
    resp = await async_client.get("/listings")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_request_with_valid_jwt_sets_tenant(async_client, tenant_auth_headers):
    resp = await async_client.get("/listings", headers=tenant_auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_tenant_a_cannot_see_tenant_b_listings(async_client, two_tenants):
    tenant_a_headers, tenant_b_headers, listing_b_id = two_tenants
    resp = await async_client.get(f"/listings/{listing_b_id}", headers=tenant_a_headers)
    assert resp.status_code == 404  # RLS hides it, not 403
