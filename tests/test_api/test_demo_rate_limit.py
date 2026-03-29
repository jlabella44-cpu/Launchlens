"""Test demo upload rate limiting."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
@patch("listingjet.api.demo._get_demo_limiter")
async def test_demo_upload_rate_limited(mock_limiter_fn, async_client):
    limiter = MagicMock()
    limiter.acquire.return_value = False
    mock_limiter_fn.return_value = limiter

    resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": [f"s3://bucket/demo/photo_{i}.jpg" for i in range(5)]},
    )
    assert resp.status_code == 429
    assert "limit" in resp.json()["detail"].lower()


@pytest.mark.asyncio
@patch("listingjet.api.demo._get_demo_limiter")
async def test_demo_upload_allowed_when_under_limit(mock_limiter_fn, async_client):
    limiter = MagicMock()
    limiter.acquire.return_value = True
    mock_limiter_fn.return_value = limiter

    resp = await async_client.post(
        "/demo/upload",
        json={"file_paths": [f"s3://bucket/demo/photo_{i}.jpg" for i in range(5)]},
    )
    assert resp.status_code == 201
    assert resp.json()["photo_count"] == 5
