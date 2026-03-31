"""Tests for the per-endpoint rate limiting dependency."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# The RateLimiter is imported *inside* the dependency function from
# listingjet.services.rate_limiter, so we patch it at that location.
_RL_PATCH = "listingjet.services.rate_limiter.RateLimiter"


@pytest.mark.asyncio
async def test_rate_limit_allows_when_under_limit():
    """When limiter.acquire returns True, the dependency should not raise."""
    from listingjet.services.endpoint_rate_limit import rate_limit

    dep = rate_limit(limit=10, period=60)

    mock_limiter = MagicMock()
    mock_limiter.acquire.return_value = True

    request = MagicMock()
    request.url.path = "/listings"
    request.state.tenant_id = "tenant-abc"

    with patch(_RL_PATCH, return_value=mock_limiter):
        await dep(request)

    mock_limiter.acquire.assert_called_once()
    call_kwargs = mock_limiter.acquire.call_args
    key = call_kwargs.kwargs.get("key", call_kwargs[1].get("key", ""))
    assert "tenant:tenant-abc" in key


@pytest.mark.asyncio
async def test_rate_limit_raises_429_when_exceeded():
    """When limiter.acquire returns False, dependency should raise HTTP 429."""
    from listingjet.services.endpoint_rate_limit import rate_limit

    dep = rate_limit(limit=5, period=60)

    mock_limiter = MagicMock()
    mock_limiter.acquire.return_value = False

    request = MagicMock()
    request.url.path = "/listings"
    request.state.tenant_id = "tenant-xyz"

    with patch(_RL_PATCH, return_value=mock_limiter):
        with pytest.raises(HTTPException) as exc_info:
            await dep(request)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail


@pytest.mark.asyncio
async def test_rate_limit_fails_open_on_redis_error():
    """If RateLimiter constructor raises, the dep should fail open (no exception)."""
    from listingjet.services.endpoint_rate_limit import rate_limit

    dep = rate_limit(limit=10, period=60)

    request = MagicMock()
    request.url.path = "/listings"
    request.state.tenant_id = "tenant-abc"

    with patch(_RL_PATCH, side_effect=Exception("Redis down")):
        # Should NOT raise — fail open
        await dep(request)


@pytest.mark.asyncio
async def test_rate_limit_uses_ip_when_no_tenant():
    """When tenant_id is absent, key should be based on client IP."""
    from listingjet.services.endpoint_rate_limit import rate_limit

    dep = rate_limit(limit=10, period=60)

    mock_limiter = MagicMock()
    mock_limiter.acquire.return_value = True

    request = MagicMock()
    request.url.path = "/demo"
    # Simulate no tenant_id on state
    del request.state.tenant_id

    with patch(_RL_PATCH, return_value=mock_limiter), \
         patch("listingjet.middleware.rate_limit._extract_client_ip", return_value="1.2.3.4"):
        await dep(request)

    key = mock_limiter.acquire.call_args.kwargs.get("key", mock_limiter.acquire.call_args[1].get("key", ""))
    assert "ip:1.2.3.4" in key
