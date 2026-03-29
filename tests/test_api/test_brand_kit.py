"""Tests for the Brand Kit API endpoints."""
import uuid
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"brand-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "BrandTester", "company_name": "BrandCo"
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
    with patch("listingjet.middleware.rate_limit._get_limiter", return_value=limiter), \
         patch("listingjet.services.rate_limiter.RateLimiter", return_value=limiter):
        yield


@pytest.mark.asyncio
async def test_get_brand_kit_initially_null(_mock_rate_limiter, async_client):
    """GET /brand-kit should return null for a new tenant."""
    token, _ = await _register(async_client)
    resp = await async_client.get("/brand-kit", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_upsert_brand_kit_creates_and_updates(_mock_rate_limiter, async_client):
    """PUT /brand-kit should create a brand kit, then update on second call."""
    token, tenant_id = await _register(async_client)

    # Create
    resp = await async_client.put("/brand-kit", json={
        "primary_color": "#2563EB",
        "agent_name": "Jane Doe",
        "brokerage_name": "Acme Realty",
    }, headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["primary_color"] == "#2563EB"
    assert data["agent_name"] == "Jane Doe"
    assert data["tenant_id"] == tenant_id

    # Update
    resp2 = await async_client.put("/brand-kit", json={
        "primary_color": "#FF0000",
        "font_primary": "Inter",
    }, headers=_auth(token))
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["primary_color"] == "#FF0000"
    assert data2["font_primary"] == "Inter"
    # agent_name should be preserved from first upsert
    assert data2["agent_name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_upsert_brand_kit_rejects_invalid_color(_mock_rate_limiter, async_client):
    """PUT /brand-kit should reject non-hex color values."""
    token, _ = await _register(async_client)

    resp = await async_client.put("/brand-kit", json={
        "primary_color": "not-a-color",
    }, headers=_auth(token))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_logo_upload_url(_mock_rate_limiter, async_client):
    """POST /brand-kit/logo-upload-url should return a presigned URL."""
    token, _ = await _register(async_client)

    mock_storage = MagicMock()
    mock_storage.presigned_upload_url.return_value = "https://s3.example.com/presigned"

    with patch("listingjet.api.brand_kit.StorageService", return_value=mock_storage):
        resp = await async_client.post("/brand-kit/logo-upload-url", headers=_auth(token))

    assert resp.status_code == 200
    data = resp.json()
    assert "key" in data
    assert data["upload"] == "https://s3.example.com/presigned"
    assert "brand-kits/" in data["key"]
