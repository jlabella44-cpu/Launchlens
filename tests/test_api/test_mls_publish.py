"""Tests for MLS publish and connections API endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from listingjet.config import settings
from listingjet.models.listing import Listing, ListingState


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post(
        "/auth/register", json={"email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo"}
    )
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- MLS Connections CRUD ---


@pytest.mark.asyncio
async def test_list_connections_empty(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.get("/mls/connections", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_connection(async_client: AsyncClient):
    token, _ = await _register(async_client)
    resp = await async_client.post(
        "/mls/connections",
        headers=_auth(token),
        json={
            "name": "Test CRMLS",
            "mls_board": "CRMLS",
            "reso_api_url": "https://api.crmls.org/reso",
            "oauth_token_url": "https://api.crmls.org/oauth2/token",
            "client_id": "my-client-id",
            "client_secret": "my-secret",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Test CRMLS"
    assert body["mls_board"] == "CRMLS"
    assert body["is_active"] is True
    assert "id" in body


@pytest.mark.asyncio
async def test_create_and_list_connections(async_client: AsyncClient):
    token, _ = await _register(async_client)
    await async_client.post(
        "/mls/connections",
        headers=_auth(token),
        json={
            "name": "Board A",
            "mls_board": "BoardA",
            "reso_api_url": "https://a.com/reso",
            "oauth_token_url": "https://a.com/oauth2/token",
            "client_id": "a-id",
            "client_secret": "a-secret",
        },
    )
    await async_client.post(
        "/mls/connections",
        headers=_auth(token),
        json={
            "name": "Board B",
            "mls_board": "BoardB",
            "reso_api_url": "https://b.com/reso",
            "oauth_token_url": "https://b.com/oauth2/token",
            "client_id": "b-id",
            "client_secret": "b-secret",
        },
    )

    resp = await async_client.get("/mls/connections", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_update_connection(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post(
        "/mls/connections",
        headers=_auth(token),
        json={
            "name": "Original",
            "mls_board": "MLS1",
            "reso_api_url": "https://mls1.com/reso",
            "oauth_token_url": "https://mls1.com/oauth2/token",
            "client_id": "cid",
            "client_secret": "csecret",
        },
    )
    conn_id = create_resp.json()["id"]

    resp = await async_client.patch(
        f"/mls/connections/{conn_id}",
        headers=_auth(token),
        json={
            "name": "Updated Name",
            "is_active": False,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_connection(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post(
        "/mls/connections",
        headers=_auth(token),
        json={
            "name": "ToDelete",
            "mls_board": "MLS",
            "reso_api_url": "https://del.com/reso",
            "oauth_token_url": "https://del.com/oauth2/token",
            "client_id": "cid",
            "client_secret": "csecret",
        },
    )
    conn_id = create_resp.json()["id"]

    resp = await async_client.delete(f"/mls/connections/{conn_id}", headers=_auth(token))
    assert resp.status_code == 204

    list_resp = await async_client.get("/mls/connections", headers=_auth(token))
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_connection_tenant_isolation(async_client: AsyncClient):
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)

    # Create connection for tenant A
    create_resp = await async_client.post(
        "/mls/connections",
        headers=_auth(token_a),
        json={
            "name": "A's MLS",
            "mls_board": "MLS-A",
            "reso_api_url": "https://a.com/reso",
            "oauth_token_url": "https://a.com/oauth2/token",
            "client_id": "a-id",
            "client_secret": "a-secret",
        },
    )
    conn_id = create_resp.json()["id"]

    # Tenant B should not see it
    resp = await async_client.get("/mls/connections", headers=_auth(token_b))
    assert resp.json() == []

    # Tenant B should not be able to get it by ID
    resp = await async_client.get(f"/mls/connections/{conn_id}", headers=_auth(token_b))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_test_connection_endpoint(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post(
        "/mls/connections",
        headers=_auth(token),
        json={
            "name": "TestConn",
            "mls_board": "MLS",
            "reso_api_url": "https://test.com/reso",
            "oauth_token_url": "https://test.com/oauth2/token",
            "client_id": "cid",
            "client_secret": "csecret",
        },
    )
    conn_id = create_resp.json()["id"]

    # Mock the RESO adapter test
    with patch("listingjet.api.mls_publish.RESOAdapter") as MockAdapter:
        instance = MockAdapter.return_value
        instance.test_connection = AsyncMock(
            return_value={
                "status": "ok",
                "response_code": 200,
                "tested_at": "2026-04-08T12:00:00Z",
            }
        )

        resp = await async_client.post(f"/mls/connections/{conn_id}/test", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["connection_id"] == conn_id


# --- Publish Endpoint ---


@pytest.mark.asyncio
async def test_publish_requires_auth(async_client: AsyncClient):
    resp = await async_client.post(f"/listings/{uuid.uuid4()}/publish")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_publish_requires_deliverable_listing(async_client: AsyncClient):
    token, tid = await _register(async_client)

    # Create a NEW listing (not publishable)
    create_resp = await async_client.post(
        "/listings",
        headers=_auth(token),
        json={
            "address": {"street": "1 Test St", "city": "Denver", "state": "CO"},
            "metadata": {},
        },
    )
    listing_id = create_resp.json()["id"]

    resp = await async_client.post(f"/listings/{listing_id}/publish", headers=_auth(token))
    assert resp.status_code == 409
    assert "Cannot publish" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_publish_requires_mls_connection(async_client: AsyncClient, db_session):
    token, tid = await _register(async_client)

    # Create a DELIVERED listing directly in DB
    listing = Listing(
        tenant_id=tid,
        address={"street": "100 Pub St", "city": "Miami", "state": "FL"},
        metadata_={"beds": 3},
        state=ListingState.DELIVERED,
    )
    db_session.add(listing)
    await db_session.commit()

    resp = await async_client.post(f"/listings/{listing.id}/publish", headers=_auth(token))
    assert resp.status_code == 400
    assert "No active MLS connection" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_publish_status_empty(async_client: AsyncClient):
    token, tid = await _register(async_client)

    create_resp = await async_client.post(
        "/listings",
        headers=_auth(token),
        json={
            "address": {"street": "1 Status St"},
            "metadata": {},
        },
    )
    listing_id = create_resp.json()["id"]

    resp = await async_client.get(f"/listings/{listing_id}/publish-status", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []
