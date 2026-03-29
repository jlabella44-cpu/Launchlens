"""Test tenant settings API."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"settings-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "SettingsCo"
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
async def test_get_settings(_mock_rate_limiter, async_client):
    token, tenant_id = await _register(async_client)
    resp = await async_client.get("/settings", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == tenant_id
    assert data["webhook_url"] is None


@pytest.mark.asyncio
async def test_update_webhook_url(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    resp = await async_client.patch(
        "/settings",
        json={"webhook_url": "https://example.com/hook"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["webhook_url"] == "https://example.com/hook"

    # Verify it persists
    resp2 = await async_client.get("/settings", headers=_auth(token))
    assert resp2.json()["webhook_url"] == "https://example.com/hook"


@pytest.mark.asyncio
async def test_clear_webhook_url(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    # Set it
    await async_client.patch(
        "/settings",
        json={"webhook_url": "https://example.com/hook"},
        headers=_auth(token),
    )

    # Clear it with empty string
    resp = await async_client.patch(
        "/settings",
        json={"webhook_url": ""},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["webhook_url"] is None


@pytest.mark.asyncio
async def test_test_webhook_no_url(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    resp = await async_client.post("/settings/test-webhook", headers=_auth(token))
    assert resp.status_code == 400
    assert "No webhook URL" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_test_webhook_success(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    # Set webhook URL
    await async_client.patch(
        "/settings",
        json={"webhook_url": "https://example.com/hook"},
        headers=_auth(token),
    )

    # Mock the delivery
    with patch("listingjet.services.webhook_delivery.deliver_webhook", new_callable=AsyncMock, return_value=True):
        resp = await async_client.post("/settings/test-webhook", headers=_auth(token))

    assert resp.status_code == 200
    assert resp.json()["delivered"] is True
