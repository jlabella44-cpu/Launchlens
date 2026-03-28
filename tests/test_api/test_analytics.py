"""Test analytics API."""
import uuid
from unittest.mock import patch, MagicMock

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from launchlens.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"analytics-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Analyst", "company_name": "AnalyticsCo"
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def _mock_rate_limiter():
    limiter = MagicMock()
    limiter.acquire.return_value = True
    with patch("launchlens.middleware.rate_limit._get_limiter", return_value=limiter):
        yield


@pytest.mark.asyncio
async def test_overview_empty(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    resp = await async_client.get("/analytics/overview", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_listings"] == 0
    assert data["delivered"] == 0
    assert data["success_rate_pct"] is None


@pytest.mark.asyncio
async def test_overview_with_listings(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    # Create some listings
    for i in range(3):
        await async_client.post("/listings", json={
            "address": {"street": f"{i}00 Analytics St", "city": "Austin", "state": "TX"},
            "metadata": {"beds": 3, "baths": 2},
        }, headers=_auth(token))

    resp = await async_client.get("/analytics/overview", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_listings"] == 3
    assert data["by_state"]["new"] == 3


@pytest.mark.asyncio
async def test_timeline(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    await async_client.post("/listings", json={
        "address": {"street": "1 Timeline St", "city": "Denver", "state": "CO"},
        "metadata": {},
    }, headers=_auth(token))

    resp = await async_client.get("/analytics/timeline?days=7", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 7
    assert len(data["data"]) >= 1
    assert data["data"][0]["count"] >= 1
