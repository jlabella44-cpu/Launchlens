import uuid

import jwt as pyjwt
import pytest
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy import select

from launchlens.config import settings
from launchlens.models.listing import Listing, ListingState


async def _register(client: AsyncClient) -> tuple[str, str]:
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "Tester", "company_name": "Export Co"
    })
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_and_prepare_listing(
    client: AsyncClient,
    db_session,
    token: str,
    tenant_id: str,
    state: ListingState,
    mls_path: str | None = None,
    mkt_path: str | None = None,
):
    """Create a listing via the API, then update state and bundle paths in DB."""
    resp = await client.post("/listings", json={
        "address": {"street": "789 Pine", "city": "Austin", "state": "TX"},
        "metadata": {"beds": 3, "baths": 2},
    }, headers=_auth(token))
    listing_id = resp.json()["id"]

    # Update state and bundle paths directly in DB
    result = await db_session.execute(
        select(Listing).where(Listing.id == uuid.UUID(listing_id))
    )
    listing = result.scalar_one()
    listing.state = state
    listing.mls_bundle_path = mls_path
    listing.marketing_bundle_path = mkt_path
    await db_session.commit()
    return listing


@pytest.mark.asyncio
@patch("launchlens.api.listings.StorageService")
async def test_export_returns_mls_bundle(mock_storage_cls, async_client, db_session):
    mock_storage_cls.return_value.presigned_url.return_value = "https://s3.example.com/presigned"
    token, tenant_id = await _register(async_client)
    listing = await _create_and_prepare_listing(
        async_client, db_session, token, tenant_id,
        state=ListingState.DELIVERED,
        mls_path="listings/abc/mls_bundle.zip",
        mkt_path="listings/abc/marketing_bundle.zip",
    )
    resp = await async_client.get(
        f"/listings/{listing.id}/export?mode=mls", headers=_auth(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "mls"
    assert data["download_url"] == "https://s3.example.com/presigned"
    assert data["listing_id"] == str(listing.id)


@pytest.mark.asyncio
@patch("launchlens.api.listings.StorageService")
async def test_export_defaults_to_marketing(mock_storage_cls, async_client, db_session):
    mock_storage_cls.return_value.presigned_url.return_value = "https://s3.example.com/presigned"
    token, tenant_id = await _register(async_client)
    listing = await _create_and_prepare_listing(
        async_client, db_session, token, tenant_id,
        state=ListingState.DELIVERED,
        mls_path="listings/abc/mls_bundle.zip",
        mkt_path="listings/abc/marketing_bundle.zip",
    )
    resp = await async_client.get(
        f"/listings/{listing.id}/export", headers=_auth(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "marketing"


@pytest.mark.asyncio
@patch("launchlens.api.listings.StorageService")
async def test_export_404_when_no_bundle(mock_storage_cls, async_client, db_session):
    token, tenant_id = await _register(async_client)
    listing = await _create_and_prepare_listing(
        async_client, db_session, token, tenant_id,
        state=ListingState.APPROVED,
        mls_path=None,
        mkt_path=None,
    )
    resp = await async_client.get(
        f"/listings/{listing.id}/export?mode=mls", headers=_auth(token)
    )
    assert resp.status_code == 404
    assert "Export not yet generated" in resp.json()["detail"]


@pytest.mark.asyncio
@patch("launchlens.api.listings.StorageService")
async def test_export_409_when_not_approved(mock_storage_cls, async_client, db_session):
    token, tenant_id = await _register(async_client)
    listing = await _create_and_prepare_listing(
        async_client, db_session, token, tenant_id,
        state=ListingState.ANALYZING,
        mls_path="listings/abc/mls_bundle.zip",
        mkt_path="listings/abc/marketing_bundle.zip",
    )
    resp = await async_client.get(
        f"/listings/{listing.id}/export?mode=mls", headers=_auth(token)
    )
    assert resp.status_code == 409
    assert "Cannot export" in resp.json()["detail"]
