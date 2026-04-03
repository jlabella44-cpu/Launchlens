"""Test activity log, usage endpoint, and API key management."""
import uuid

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"activ-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "ActivityCo"
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


# --- Activity Log ---

@pytest.mark.asyncio
async def test_activity_log_empty(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    # Create a listing
    resp = await async_client.post("/listings", json={
        "address": {"street": "1 Log St"}, "metadata": {},
    }, headers=_auth(token))
    lid = resp.json()["id"]

    resp = await async_client.get(f"/listings/{lid}/activity", headers=_auth(token))
    assert resp.status_code == 200
    # New listing has no pipeline events yet
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_activity_log_not_found(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(f"/listings/{fake_id}/activity", headers=_auth(token))
    assert resp.status_code == 404


# --- Usage ---

@pytest.mark.asyncio
async def test_usage_empty(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    resp = await async_client.get("/settings/usage", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "starter"
    assert data["listings"]["used"] == 0
    assert data["listings"]["limit"] == 5


@pytest.mark.asyncio
async def test_usage_counts_listings(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    for i in range(2):
        await async_client.post("/listings", json={
            "address": {"street": f"{i} Usage St"}, "metadata": {},
        }, headers=_auth(token))

    resp = await async_client.get("/settings/usage", headers=_auth(token))
    data = resp.json()
    assert data["listings"]["used"] == 2
    assert data["listings"]["remaining"] == 3


# --- API Keys ---

@pytest.mark.asyncio
async def test_create_api_key(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    resp = await async_client.post(
        "/settings/api-keys",
        json={"name": "My CRM Integration"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My CRM Integration"
    assert data["key"].startswith("ll_")
    assert "warning" in data


@pytest.mark.asyncio
async def test_list_api_keys(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    # Create two keys
    await async_client.post("/settings/api-keys", json={"name": "Key 1"}, headers=_auth(token))
    await async_client.post("/settings/api-keys", json={"name": "Key 2"}, headers=_auth(token))

    resp = await async_client.get("/settings/api-keys", headers=_auth(token))
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) == 2
    # Should not expose the key hash or plaintext
    assert "key" not in keys[0]
    assert "key_hash" not in keys[0]


@pytest.mark.asyncio
async def test_revoke_api_key(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    create_resp = await async_client.post(
        "/settings/api-keys", json={"name": "Temp Key"}, headers=_auth(token)
    )
    key_id = create_resp.json()["id"]

    resp = await async_client.delete(f"/settings/api-keys/{key_id}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["revoked"] is True

    # Verify it's inactive in the list
    list_resp = await async_client.get("/settings/api-keys", headers=_auth(token))
    keys = list_resp.json()
    revoked = [k for k in keys if k["id"] == key_id]
    assert len(revoked) == 1
    assert revoked[0]["is_active"] is False


@pytest.mark.asyncio
async def test_revoke_nonexistent_key(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    fake_id = str(uuid.uuid4())
    resp = await async_client.delete(f"/settings/api-keys/{fake_id}", headers=_auth(token))
    assert resp.status_code == 404
