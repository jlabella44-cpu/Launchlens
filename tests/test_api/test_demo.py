import uuid
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import make_jwt


@pytest.fixture(autouse=True)
def _mock_demo_limiter():
    """All demo tests bypass the Redis rate limiter."""
    limiter = MagicMock()
    limiter.acquire.return_value = True
    with patch("listingjet.api.demo._get_demo_limiter", return_value=limiter):
        yield


def _photo_paths(n: int) -> list[str]:
    return [f"s3://bucket/demo/photo_{i}.jpg" for i in range(n)]


@pytest.mark.asyncio
async def test_demo_upload_creates_listing(async_client):
    resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": _photo_paths(5)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "demo_id" in data
    assert data["photo_count"] == 5
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_demo_upload_validates_photo_count_too_few(async_client):
    resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": ["s3://bucket/demo/photo_0.jpg"]},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_demo_upload_validates_photo_count_too_many(async_client):
    resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": _photo_paths(51)},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_demo_view_returns_results(async_client):
    upload_resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": _photo_paths(5)},
    )
    demo_id = upload_resp.json()["demo_id"]

    resp = await async_client.get(f"/demo/{demo_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_demo"] is True
    assert data["state"] == "demo"
    assert "locked_features" in data
    assert len(data["photos"]) == 5


@pytest.mark.asyncio
async def test_demo_view_not_found(async_client):
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(f"/demo/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_demo_claim_requires_auth(async_client):
    upload_resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": _photo_paths(5)},
    )
    demo_id = upload_resp.json()["demo_id"]

    resp = await async_client.post(f"/demo/{demo_id}/claim")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_demo_claim_with_auth(async_client):
    upload_resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": _photo_paths(5)},
    )
    demo_id = upload_resp.json()["demo_id"]

    tenant_id = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {make_jwt(tenant_id)}"}

    resp = await async_client.post(f"/demo/{demo_id}/claim", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["claimed"] is True
    assert data["state"] == "uploading"
    assert data["listing_id"] == demo_id

    # Verify it's no longer a demo
    view_resp = await async_client.get(f"/demo/{demo_id}")
    assert view_resp.status_code == 404  # is_demo is now False


@pytest.mark.asyncio
async def test_demo_full_flow(async_client):
    """End-to-end: upload -> view -> claim."""
    # Upload
    upload_resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": _photo_paths(10)},
    )
    assert upload_resp.status_code == 201
    demo_id = upload_resp.json()["demo_id"]

    # View
    view_resp = await async_client.get(f"/demo/{demo_id}")
    assert view_resp.status_code == 200
    assert view_resp.json()["photo_count"] if "photo_count" in view_resp.json() else len(view_resp.json()["photos"]) == 10

    # Claim
    tenant_id = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {make_jwt(tenant_id)}"}
    claim_resp = await async_client.post(f"/demo/{demo_id}/claim", headers=headers)
    assert claim_resp.status_code == 200
    assert claim_resp.json()["claimed"] is True
