"""Test enhanced billing endpoints."""
import uuid
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"billing-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Biller", "company_name": "BillCo"
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
    with patch("listingjet.middleware.rate_limit._get_limiter", return_value=limiter):
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
    """Already on starter → can't change to starter."""
    token, _ = await _register(async_client)
    resp = await async_client.post(
        "/billing/change-plan",
        json={"plan": "starter"},
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
    assert data["plan"] == "starter"
    assert data["stripe_customer_id"] is None
