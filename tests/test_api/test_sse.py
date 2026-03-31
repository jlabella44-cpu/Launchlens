# tests/test_api/test_sse.py
"""Tests for the SSE endpoint GET /sse/listings/{id}/events."""
import asyncio
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> tuple[str, str]:
    import jwt as pyjwt

    from listingjet.config import settings

    email = f"sse-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "SSE Tester", "company_name": "SSE Co"
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return token, payload["tenant_id"]


async def _create_listing(client: AsyncClient, token: str) -> str:
    resp = await client.post("/listings", json={
        "address": {"street": "1 SSE Lane", "city": "Austin", "state": "TX", "zip": "78701"},
        "metadata": {"beds": 3, "baths": 2, "sqft": 1500, "price": 350000},
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_sse_requires_auth(async_client: AsyncClient):
    """Unauthenticated request returns 401 or 403."""
    listing_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/sse/listings/{listing_id}/events",
        headers={},
        timeout=3.0,
    )
    assert resp.status_code in (401, 403)


@pytest.mark.skip(reason="SSE streaming hangs in CI — no real disconnect detection")
@pytest.mark.asyncio
async def test_sse_returns_event_stream_content_type(async_client: AsyncClient):
    """Authenticated request for existing listing returns text/event-stream."""
    token, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    async with asyncio.timeout(10):
        async with async_client.stream(
            "GET",
            f"/sse/listings/{listing_id}/events",
            headers={"Authorization": f"Bearer {token}"},
            timeout=3.0,
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_sse_returns_404_for_missing_listing(async_client: AsyncClient):
    """Non-existent listing returns 404."""
    token, _ = await _register(async_client)
    missing_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/sse/listings/{missing_id}/events",
        headers={"Authorization": f"Bearer {token}"},
        timeout=3.0,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sse_returns_404_for_other_tenant_listing(async_client: AsyncClient):
    """A listing owned by another tenant returns 404 (not 403) to avoid enumeration."""
    token_a, _ = await _register(async_client)
    token_b, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token_a)

    resp = await async_client.get(
        f"/sse/listings/{listing_id}/events",
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=3.0,
    )
    assert resp.status_code == 404


@pytest.mark.skip(reason="SSE streaming hangs in CI — no real disconnect detection")
@pytest.mark.asyncio
async def test_sse_streams_retry_directive(async_client: AsyncClient):
    """Initial SSE frame includes retry directive."""
    token, _ = await _register(async_client)
    listing_id = await _create_listing(async_client, token)

    chunks = []
    async with asyncio.timeout(10):
        async with async_client.stream(
            "GET",
            f"/sse/listings/{listing_id}/events",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        ) as resp:
            assert resp.status_code == 200
            async for chunk in resp.aiter_text():
                chunks.append(chunk)
                break  # read just first chunk

    first = "".join(chunks)
    assert "retry:" in first
