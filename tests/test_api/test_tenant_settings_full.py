"""Extended tests for tenant settings API — usage and api-keys endpoints."""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"setfull-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "SettingsFullTester", "company_name": "FullCo",
        "plan_tier": "free",
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _fund_account(db_session, tenant_id: str, amount: int = 10):
    """Give tenant credits via the service."""
    from listingjet.services.credits import CreditService
    svc = CreditService()
    await svc.ensure_account(db_session, uuid.UUID(tenant_id))
    await svc.add_credits(
        db_session, uuid.UUID(tenant_id), amount,
        transaction_type="purchase",
        reference_id=str(uuid.uuid4()),
    )
    await db_session.commit()


@pytest.fixture
def _mock_rate_limiter():
    """Rate limiting is handled by the autouse _mock_redis_globally fixture."""
    yield


# --- Usage ---

@pytest.mark.asyncio
async def test_usage_reflects_created_listings(_mock_rate_limiter, async_client, db_session):
    """GET /settings/usage should count listings created in current month."""
    token, tenant_id = await _register(async_client)
    await _fund_account(db_session, tenant_id, amount=10)

    # Create 2 listings and verify they succeed
    for i in range(2):
        create_resp = await async_client.post("/listings", json={
            "address": {"street": f"{i} Full St"}, "metadata": {},
        }, headers=_auth(token))
        assert create_resp.status_code in (200, 201), f"Listing creation failed: {create_resp.text}"

    resp = await async_client.get("/settings/usage", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "free"
    assert data["listings"]["used"] == 2
    assert data["listings"]["limit"] == 5
    assert data["listings"]["remaining"] == 3
    assert data["features"]["tier2_vision"] is False
    assert data["features"]["social_content"] is False


@pytest.mark.asyncio
async def test_usage_new_tenant_zero(_mock_rate_limiter, async_client):
    """A brand new tenant should have 0 used listings."""
    token, _ = await _register(async_client)
    resp = await async_client.get("/settings/usage", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["listings"]["used"] == 0
    assert "period" in data


# --- API Keys ---

@pytest.mark.asyncio
async def test_api_key_full_lifecycle(_mock_rate_limiter, async_client):
    """Create, list, and revoke an API key through the settings endpoints."""
    token, _ = await _register(async_client)

    # Create
    create_resp = await async_client.post(
        "/settings/api-keys",
        json={"name": "CI/CD Key"},
        headers=_auth(token),
    )
    assert create_resp.status_code == 201
    key_data = create_resp.json()
    assert key_data["name"] == "CI/CD Key"
    assert key_data["key"].startswith("ll_")
    key_id = key_data["id"]

    # List
    list_resp = await async_client.get("/settings/api-keys", headers=_auth(token))
    assert list_resp.status_code == 200
    keys = list_resp.json()
    assert any(k["id"] == key_id for k in keys)
    # Plaintext key should NOT appear in list
    for k in keys:
        assert "key" not in k

    # Revoke
    revoke_resp = await async_client.delete(
        f"/settings/api-keys/{key_id}", headers=_auth(token)
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["revoked"] is True

    # Confirm revoked in list
    list_resp2 = await async_client.get("/settings/api-keys", headers=_auth(token))
    revoked = [k for k in list_resp2.json() if k["id"] == key_id]
    assert revoked[0]["is_active"] is False


@pytest.mark.asyncio
async def test_revoke_other_tenants_key_404(_mock_rate_limiter, async_client):
    """Revoking a key that belongs to another tenant should return 404."""
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)

    # Create key under tenant A
    create_resp = await async_client.post(
        "/settings/api-keys",
        json={"name": "A's Key"},
        headers=_auth(token_a),
    )
    key_id = create_resp.json()["id"]

    # Tenant B tries to revoke it
    resp = await async_client.delete(
        f"/settings/api-keys/{key_id}", headers=_auth(token_b)
    )
    assert resp.status_code == 404
