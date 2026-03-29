"""Test bulk operations API."""
import uuid
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"bulk-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Bulker", "company_name": "BulkCo"
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
async def test_bulk_approve_not_found(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    fake_id = str(uuid.uuid4())
    resp = await async_client.post(
        "/bulk/approve",
        json={"listing_ids": [fake_id]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved"] == 0
    assert data["results"][0]["status"] == "not_found"


@pytest.mark.asyncio
async def test_bulk_approve_wrong_state(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    # Create a listing (state=new, not in_review)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "1 Bulk St", "city": "Austin", "state": "TX"},
        "metadata": {},
    }, headers=_auth(token))
    lid = create_resp.json()["id"]

    resp = await async_client.post(
        "/bulk/approve",
        json={"listing_ids": [lid]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved"] == 0
    assert data["results"][0]["status"] == "skipped"


@pytest.mark.asyncio
async def test_bulk_approve_max_limit(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)
    ids = [str(uuid.uuid4()) for _ in range(51)]
    resp = await async_client.post(
        "/bulk/approve",
        json={"listing_ids": ids},
        headers=_auth(token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_bulk_export_no_bundle(_mock_rate_limiter, async_client):
    token, _ = await _register(async_client)

    create_resp = await async_client.post("/listings", json={
        "address": {"street": "2 Bulk St", "city": "Denver", "state": "CO"},
        "metadata": {},
    }, headers=_auth(token))
    lid = create_resp.json()["id"]

    resp = await async_client.post(
        "/bulk/export",
        json={"listing_ids": [lid], "mode": "mls"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] == 0
    assert data["results"][0]["status"] == "no_bundle"
