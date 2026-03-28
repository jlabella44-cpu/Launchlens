# tests/test_api/test_video.py
import uuid

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
async def test_get_video_not_ready(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "No Video St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    resp = await async_client.get(f"/listings/{listing_id}/video", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_social_cuts_not_ready(async_client: AsyncClient):
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "No Cuts St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    resp = await async_client.get(f"/listings/{listing_id}/video/social-cuts", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_video_upload_endpoint_exists(async_client: AsyncClient):
    """POST /listings/{id}/video/upload should exist (even if it returns 404 for missing listing)."""
    token, _ = await _register(async_client)
    fake_id = uuid.uuid4()
    resp = await async_client.post(
        f"/listings/{fake_id}/video/upload",
        json={"s3_key": f"videos/{fake_id}/tour.mp4", "video_type": "professional"},
        headers=_auth(token),
    )
    assert resp.status_code == 404  # listing not found, but route exists


@pytest.mark.asyncio
async def test_video_upload_rejects_bad_s3_key(async_client: AsyncClient):
    """S3 key must be scoped to the listing's namespace."""
    token, _ = await _register(async_client)
    create_resp = await async_client.post("/listings", json={
        "address": {"street": "Upload St"}, "metadata": {},
    }, headers=_auth(token))
    listing_id = create_resp.json()["id"]
    resp = await async_client.post(
        f"/listings/{listing_id}/video/upload",
        json={"s3_key": "videos/other-tenant/evil.mp4", "video_type": "professional"},
        headers=_auth(token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_video_requires_auth(async_client: AsyncClient):
    resp = await async_client.get(f"/listings/{uuid.uuid4()}/video")
    assert resp.status_code == 401
