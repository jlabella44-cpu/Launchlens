"""Tests for SecurityHeadersMiddleware."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_security_headers_present(async_client: AsyncClient):
    """All security headers should be set on every response."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200

    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-XSS-Protection"] == "1; mode=block"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in resp.headers["Permissions-Policy"]
    assert "microphone=()" in resp.headers["Permissions-Policy"]
    assert "includeSubDomains" in resp.headers["Strict-Transport-Security"]
    assert "frame-ancestors" in resp.headers["Content-Security-Policy"]


@pytest.mark.asyncio
async def test_security_headers_on_error(async_client: AsyncClient):
    """Security headers should also be present on error responses."""
    resp = await async_client.get("/nonexistent-route-xyz")
    # Even on 404/405, headers should be set
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
