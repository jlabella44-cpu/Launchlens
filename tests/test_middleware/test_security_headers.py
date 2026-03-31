# tests/test_middleware/test_security_headers.py
"""Tests for SecurityHeadersMiddleware — verifies headers on all responses."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hsts_header_present(async_client: AsyncClient):
    """Strict-Transport-Security header is present on all responses."""
    resp = await async_client.get("/health")
    assert "strict-transport-security" in resp.headers
    assert "max-age=" in resp.headers["strict-transport-security"]


@pytest.mark.asyncio
async def test_x_content_type_options_nosniff(async_client: AsyncClient):
    """X-Content-Type-Options is set to nosniff."""
    resp = await async_client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"


@pytest.mark.asyncio
async def test_x_frame_options_deny(async_client: AsyncClient):
    """X-Frame-Options is set to DENY."""
    resp = await async_client.get("/health")
    assert resp.headers.get("x-frame-options") == "DENY"


@pytest.mark.asyncio
async def test_csp_header_present(async_client: AsyncClient):
    """Content-Security-Policy header is present."""
    resp = await async_client.get("/health")
    assert "content-security-policy" in resp.headers
    assert "frame-ancestors" in resp.headers["content-security-policy"]


@pytest.mark.asyncio
async def test_referrer_policy_present(async_client: AsyncClient):
    """Referrer-Policy header is set."""
    resp = await async_client.get("/health")
    assert "referrer-policy" in resp.headers


@pytest.mark.asyncio
async def test_permissions_policy_present(async_client: AsyncClient):
    """Permissions-Policy header restricts camera/mic/geo."""
    resp = await async_client.get("/health")
    policy = resp.headers.get("permissions-policy", "")
    assert "camera=()" in policy
    assert "microphone=()" in policy
    assert "geolocation=()" in policy


@pytest.mark.asyncio
async def test_security_headers_on_404(async_client: AsyncClient):
    """Security headers are added even on 404 responses."""
    resp = await async_client.get("/nonexistent-endpoint-xyz")
    assert "x-content-type-options" in resp.headers
    assert "strict-transport-security" in resp.headers


@pytest.mark.asyncio
async def test_security_headers_on_post(async_client: AsyncClient):
    """Security headers are present on POST responses too."""
    resp = await async_client.post("/auth/login", json={"email": "x@x.com", "password": "badpass"})
    assert "x-content-type-options" in resp.headers
    assert "content-security-policy" in resp.headers
