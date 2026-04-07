"""Upload edge-case tests — file limits, extensions, and asset registration."""
import uuid
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from listingjet.config import settings
from listingjet.models.asset import Asset


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "UploadCo",
        "plan_tier": "free",
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_listing(client: AsyncClient, token: str) -> str:
    resp = await client.post("/listings", json={
        "address": {"street": "1 Upload St"}, "metadata": {},
    }, headers=_auth(token))
    return resp.json()["id"]


# --- upload-urls file count limits ---


@pytest.mark.asyncio
@patch("listingjet.api.listings_media.get_storage")
async def test_upload_urls_max_50_files_succeeds(MockStorage, async_client: AsyncClient):
    """Request presigned URLs for exactly 50 files → 200 with 50 URLs."""
    mock_svc = MockStorage.return_value
    mock_svc.presigned_upload_url.return_value = "https://s3.example.com/presigned"

    token, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    filenames = [f"photo_{i}.jpg" for i in range(50)]
    resp = await async_client.post(
        f"/listings/{listing_id}/upload-urls",
        json={"filenames": filenames},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()["upload_urls"]) == 50


@pytest.mark.asyncio
async def test_upload_urls_51_files_returns_400(async_client: AsyncClient):
    """Request presigned URLs for 51 files → 400."""
    token, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    filenames = [f"photo_{i}.jpg" for i in range(51)]
    resp = await async_client.post(
        f"/listings/{listing_id}/upload-urls",
        json={"filenames": filenames},
        headers=_auth(token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_urls_zero_files_returns_400(async_client: AsyncClient):
    """Request with empty file list → 400."""
    token, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    resp = await async_client.post(
        f"/listings/{listing_id}/upload-urls",
        json={"filenames": []},
        headers=_auth(token),
    )
    assert resp.status_code == 400


# --- extension validation ---


@pytest.mark.asyncio
@patch("listingjet.api.listings_media.get_storage")
async def test_upload_urls_invalid_extension_returns_400(MockStorage, async_client: AsyncClient):
    """Request URL for 'photo.gif' → 400 with message about allowed extensions."""
    mock_svc = MockStorage.return_value
    mock_svc.presigned_upload_url.return_value = "https://s3.example.com/presigned"

    token, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    resp = await async_client.post(
        f"/listings/{listing_id}/upload-urls",
        json={"filenames": ["photo.gif"]},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    assert "Allowed" in resp.json()["detail"] or "Invalid" in resp.json()["detail"]


@pytest.mark.asyncio
@patch("listingjet.api.listings_media.get_storage")
async def test_upload_urls_valid_extensions_accepted(MockStorage, async_client: AsyncClient):
    """Test .jpg, .jpeg, .png all succeed."""
    mock_svc = MockStorage.return_value
    mock_svc.presigned_upload_url.return_value = "https://s3.example.com/presigned"

    token, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    resp = await async_client.post(
        f"/listings/{listing_id}/upload-urls",
        json={"filenames": ["a.jpg", "b.jpeg", "c.png"]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    urls = resp.json()["upload_urls"]
    assert len(urls) == 3


# --- register assets ---


@pytest.mark.asyncio
@patch("listingjet.api.listings_media.get_temporal_client")
async def test_register_assets_creates_records(mock_get_client, async_client: AsyncClient, db_session):
    """Register 3 assets → 3 Asset records in DB with correct listing_id."""
    mock_client = AsyncMock()
    mock_get_client.return_value = mock_client

    token, tenant_id = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    resp = await async_client.post(f"/listings/{listing_id}/assets", json={
        "assets": [
            {"file_path": "s3://bucket/img1.jpg", "file_hash": "hash1"},
            {"file_path": "s3://bucket/img2.jpg", "file_hash": "hash2"},
            {"file_path": "s3://bucket/img3.jpg", "file_hash": "hash3"},
        ]
    }, headers=_auth(token))
    assert resp.status_code == 201
    assert resp.json()["count"] == 3

    # Verify DB records
    result = await db_session.execute(
        select(Asset).where(Asset.listing_id == uuid.UUID(listing_id))
    )
    assets = list(result.scalars().all())
    assert len(assets) == 3
    for a in assets:
        assert str(a.listing_id) == listing_id
        assert a.state == "uploaded"
