# tests/test_middleware/test_tenant.py
import uuid
import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    """Register a user, return token."""
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo"
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_request_without_auth_returns_401(async_client):
    resp = await async_client.get("/listings")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_request_with_valid_jwt_sets_tenant(async_client):
    token = await _register(async_client)
    resp = await async_client.get("/listings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_tenant_a_cannot_see_tenant_b_listings(async_client):
    token_a = await _register(async_client)
    token_b = await _register(async_client)
    # Create listing as tenant B
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "123 Main St"}, "metadata": {},
    }, headers={"Authorization": f"Bearer {token_b}"})
    listing_b_id = create_resp.json()["id"]
    # Tenant A should not see it
    resp = await async_client.get(f"/listings/{listing_b_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 404
