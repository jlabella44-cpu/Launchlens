import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unlisted_vercel_origin_gets_no_cors_headers(async_client: AsyncClient):
    resp = await async_client.options(
        "/health",
        headers={
            "Origin": "https://listingjet-attacker.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in resp.headers


@pytest.mark.asyncio
async def test_configured_origin_gets_cors_headers(async_client: AsyncClient):
    from listingjet.config import settings
    origin = settings.cors_origins.split(",")[0].strip()
    resp = await async_client.options(
        "/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert resp.headers.get("access-control-allow-origin") == origin
