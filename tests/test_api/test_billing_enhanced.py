"""Test enhanced billing endpoints."""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"billing-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Biller", "company_name": "BillCo",
        "plan_tier": "free",
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def _mock_rate_limiter():
    """Rate limiting is handled by the autouse _mock_redis_globally fixture."""
    yield


@pytest.mark.asyncio
async def test_invoices_no_customer(_mock_rate_limiter, async_client):
    """No Stripe customer yet → returns empty list."""
    token, _ = await _register(async_client)
    resp = await async_client.get("/billing/invoices", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["invoices"] == []


@pytest.mark.asyncio
async def test_change_plan_no_subscription(_mock_rate_limiter, async_client):
    """Can't change plan without an active subscription."""
    token, _ = await _register(async_client)
    resp = await async_client.post(
        "/billing/change-plan",
        json={"plan": "pro"},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    assert "No active subscription" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_change_plan_invalid(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    resp = await async_client.post(
        "/billing/change-plan",
        json={"plan": "ultra"},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    assert "Invalid plan" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_change_plan_same_plan(_mock_rate_limiter, async_client):
    """Already on free → can't change to free."""
    token, _ = await _register(async_client)
    resp = await async_client.post(
        "/billing/change-plan",
        json={"plan": "free"},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    assert "Already on" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_status_returns_plan(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    resp = await async_client.get("/billing/status", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "free"
    assert data["has_payment_method"] is False
    assert data["has_subscription"] is False
