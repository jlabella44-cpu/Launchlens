"""Tests for social publishing API endpoints."""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient, plan: str = "active_agent") -> tuple[str, str]:
    email = f"social-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "SocialCo",
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
async def test_list_social_posts_empty(async_client):
    """Empty post list for new listing."""
    token, _ = await _register(async_client)
    # Create a listing first
    resp = await async_client.post("/listings", json={
        "address": {"street": "100 Social St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}/social/posts", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_publish_requires_connected_account(async_client):
    """Publish without connected account returns 409."""
    token, _ = await _register(async_client, plan="active_agent")
    resp = await async_client.post("/listings", json={
        "address": {"street": "200 Publish St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = resp.json()["id"]

    resp = await async_client.post(
        f"/listings/{listing_id}/social/publish",
        json={"platform": "instagram", "caption": "Test post", "hashtags": [], "media_s3_keys": []},
        headers=_auth(token),
    )
    assert resp.status_code == 409
    assert "No connected" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_publish_blocked_for_free_plan(async_client):
    """Free plan users cannot publish."""
    token, _ = await _register(async_client, plan="free")
    resp = await async_client.post("/listings", json={
        "address": {"street": "300 Free St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = resp.json()["id"]

    resp = await async_client.post(
        f"/listings/{listing_id}/social/publish",
        json={"platform": "instagram", "caption": "Test", "hashtags": [], "media_s3_keys": []},
        headers=_auth(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_schedule_blocked_for_active_agent(async_client):
    """Active Agent plan cannot schedule (Team+ only)."""
    token, _ = await _register(async_client, plan="active_agent")
    resp = await async_client.post("/listings", json={
        "address": {"street": "400 Schedule St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = resp.json()["id"]

    resp = await async_client.post(
        f"/listings/{listing_id}/social/schedule",
        json={
            "platform": "instagram", "caption": "Scheduled test",
            "hashtags": [], "media_s3_keys": [],
            "scheduled_at": "2026-12-01T10:00:00Z",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_oauth_connect_blocked_for_free(async_client):
    """Free plan cannot initiate OAuth."""
    token, _ = await _register(async_client, plan="free")
    resp = await async_client.get("/social-accounts/instagram/connect", headers=_auth(token))
    assert resp.status_code == 403
