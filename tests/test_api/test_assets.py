# tests/test_api/test_assets.py
import uuid
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from httpx import AsyncClient

from launchlens.config import settings


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "TestCo"
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_assets(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "1 Photo St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [
            {"file_path": "s3://bucket/photo1.jpg", "file_hash": "aaa111"},
            {"file_path": "s3://bucket/photo2.jpg", "file_hash": "bbb222"},
        ]
    }, headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["count"] == 2
    assert body["listing_state"] == "uploading"


@pytest.mark.asyncio
async def test_list_assets(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "2 Photo St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [{"file_path": "s3://bucket/a.jpg", "file_hash": "hash1"}]
    }, headers=_auth(token))

    resp = await async_client.get(f"/listings/{listing_id}/assets", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["file_path"] == "s3://bucket/a.jpg"
    assert resp.json()[0]["state"] == "uploaded"


@pytest.mark.asyncio
async def test_register_assets_wrong_tenant(async_client: AsyncClient):
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Private St"}, "metadata": {},
    }, headers=_auth(token_a))
    listing_id = create_resp.json()["id"]

    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [{"file_path": "s3://bucket/x.jpg", "file_hash": "xxx"}]
    }, headers=_auth(token_b))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_register_assets_requires_auth(async_client: AsyncClient):
    resp = await async_client.post(f"/listings/{uuid.uuid4()}/assets", json={
        "assets": [{"file_path": "s3://x.jpg", "file_hash": "x"}]
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
@patch("launchlens.api.listings.get_temporal_client")
async def test_register_assets_triggers_pipeline(mock_get_client, async_client: AsyncClient):
    """Registering assets should start the Temporal pipeline."""
    mock_client = AsyncMock()
    mock_get_client.return_value = mock_client

    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Pipeline St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]

    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [{"file_path": "s3://bucket/photo.jpg", "file_hash": "abc"}]
    }, headers=_auth(token))
    assert resp.status_code == 201
    mock_client.start_pipeline.assert_called_once()
