"""Test listing health score and IDX feed config API endpoints."""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from listingjet.config import settings


async def _register(client: AsyncClient, test_engine, plan: str = "pro") -> tuple[str, str]:
    email = f"health-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "HealthCo"
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    tenant_id = payload["tenant_id"]

    # Upgrade tenant plan using test DB session (not AsyncSessionLocal which uses prod DB)
    if plan != "starter":
        from listingjet.models.tenant import Tenant
        session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_factory() as db:
            tenant = await db.get(Tenant, uuid.UUID(tenant_id))
            if tenant:
                tenant.plan = plan
                await db.commit()

    return token, tenant_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_health_summary_empty(async_client, test_engine):
    """Health summary with no scored listings returns zeros."""
    token, _ = await _register(async_client, test_engine)
    resp = await async_client.get("/listings/health/summary", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_scored"] == 0
    assert data["average_score"] == 0


@pytest.mark.asyncio
async def test_get_health_weights(async_client, test_engine):
    """Health weights endpoint returns weight distribution."""
    token, _ = await _register(async_client, test_engine)
    resp = await async_client.get("/settings/health-weights", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    # Pro plan has media, content, velocity, syndication
    assert data["media"] > 0
    assert data["content"] > 0
    assert abs(sum(data.values()) - 1.0) < 0.01


@pytest.mark.asyncio
async def test_update_health_weights_enterprise_only(async_client, test_engine):
    """Custom health weights require Enterprise plan."""
    token, _ = await _register(async_client, test_engine, plan="pro")
    resp = await async_client.patch(
        "/settings/health-weights",
        json={"media": 0.5, "content": 0.2, "velocity": 0.1, "syndication": 0.1, "market": 0.1},
        headers=_auth(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires cross-request session persistence — test fixture rolls back between API calls")
async def test_idx_feed_crud_pro(async_client, test_engine):
    """Pro users can create, list, and delete 1 IDX feed."""
    token, _ = await _register(async_client, test_engine, plan="pro")

    # Create
    resp = await async_client.post(
        "/settings/idx-feed",
        json={"name": "Test MLS", "base_url": "https://api.testmls.com", "api_key": "test-key-123"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    feed = resp.json()
    assert feed["name"] == "Test MLS"
    assert feed["status"] == "active"
    feed_id = feed["id"]

    # List
    resp = await async_client.get("/settings/idx-feed", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Pro: second feed should fail
    resp = await async_client.post(
        "/settings/idx-feed",
        json={"name": "Second MLS", "base_url": "https://api.other.com", "api_key": "key2"},
        headers=_auth(token),
    )
    assert resp.status_code == 409

    # Delete
    resp = await async_client.delete(f"/settings/idx-feed/{feed_id}", headers=_auth(token))
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_idx_feed_starter_blocked(async_client, test_engine):
    """Starter plan cannot create IDX feeds."""
    token, _ = await _register(async_client, test_engine, plan="starter")
    resp = await async_client.post(
        "/settings/idx-feed",
        json={"name": "MLS", "base_url": "https://api.mls.com", "api_key": "key"},
        headers=_auth(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_listing_health_not_found(async_client, test_engine):
    """Health score for non-existent listing returns 404."""
    token, _ = await _register(async_client, test_engine)
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(f"/listings/{fake_id}/health", headers=_auth(token))
    assert resp.status_code == 404
