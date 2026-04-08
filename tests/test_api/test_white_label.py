"""Tests for white-label branding API."""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient, plan: str = "team") -> tuple[str, str]:
    email = f"wl-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "WhiteLabelCo",
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    tenant_id = payload["tenant_id"]

    if plan != "free":
        from listingjet.database import AsyncSessionLocal
        from listingjet.models.tenant import Tenant
        async with AsyncSessionLocal() as db:
            tenant = await db.get(Tenant, uuid.UUID(tenant_id))
            if tenant:
                tenant.plan = plan
                await db.commit()

    return token, tenant_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_branding_returns_defaults(async_client):
    """Public /branding returns default ListingJet branding."""
    resp = await async_client.get("/branding")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app_name"] == "ListingJet"
    assert data["white_label_enabled"] is False


@pytest.mark.asyncio
async def test_white_label_blocked_for_free(async_client):
    """Free plan cannot access white-label settings."""
    token, _ = await _register(async_client, plan="free")
    resp = await async_client.get("/settings/white-label", headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_white_label_config_team(async_client):
    """Team plan can read white-label config (empty by default)."""
    token, _ = await _register(async_client, plan="team")
    resp = await async_client.get("/settings/white-label", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["white_label_enabled"] is False


@pytest.mark.asyncio
async def test_white_label_update_requires_brand_kit(async_client):
    """Cannot update white-label without an existing brand kit."""
    token, _ = await _register(async_client, plan="team")
    resp = await async_client.patch(
        "/settings/white-label",
        json={"app_name": "Acme Media OS", "white_label_enabled": True},
        headers=_auth(token),
    )
    assert resp.status_code == 404
