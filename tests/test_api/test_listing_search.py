"""Test listing search/filter/pagination."""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"search-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Searcher", "company_name": "SearchCo",
        "plan_tier": "free",
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_listing(client, token, street, city, state_abbr, listing_state=None):
    resp = await client.post("/listings", json={
        "address": {"street": street, "city": city, "state": state_abbr},
        "metadata": {"beds": 3, "baths": 2, "sqft": 1800, "price": 450000},
    }, headers=_auth(token))
    return resp.json()


@pytest.fixture
def _mock_rate_limiter():
    """Rate limiting is handled by the autouse _mock_redis_globally fixture."""
    yield


@pytest.mark.asyncio
async def test_filter_by_state(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    await _create_listing(async_client, token, "100 Oak Ln", "Austin", "TX")
    await _create_listing(async_client, token, "200 Pine St", "Denver", "CO")

    # Both are "draft" state
    resp = await async_client.get("/listings?state=draft", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2

    # No "approved" listings
    resp = await async_client.get("/listings?state=approved", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 0


@pytest.mark.asyncio
async def test_search_by_city(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    await _create_listing(async_client, token, "100 Oak Ln", "Austin", "TX")
    await _create_listing(async_client, token, "200 Pine St", "Denver", "CO")
    await _create_listing(async_client, token, "300 Elm Ave", "Austin", "TX")

    resp = await async_client.get("/listings?state=draft&search=Austin", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


@pytest.mark.asyncio
async def test_search_by_street(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    await _create_listing(async_client, token, "100 Oak Ln", "Austin", "TX")
    await _create_listing(async_client, token, "200 Pine St", "Denver", "CO")

    resp = await async_client.get("/listings?state=draft&search=Oak", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()["items"]
    assert len(data) == 1
    assert "Oak" in data[0]["address"]["street"]


@pytest.mark.asyncio
async def test_pagination(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    for i in range(5):
        await _create_listing(async_client, token, f"{i}00 Test St", "City", "TX")

    resp = await async_client.get("/listings?state=draft&page_size=2&page=1", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2

    resp2 = await async_client.get("/listings?state=draft&page_size=2&page=2", headers=_auth(token))
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 2


@pytest.mark.asyncio
async def test_combined_filters(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    await _create_listing(async_client, token, "100 Oak Ln", "Austin", "TX")
    await _create_listing(async_client, token, "200 Pine St", "Austin", "TX")

    # Both are "draft" and in Austin
    resp = await async_client.get("/listings?state=draft&search=Austin", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2

    # Search for Oak + new state
    resp = await async_client.get("/listings?state=draft&search=Oak", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
