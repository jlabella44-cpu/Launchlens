"""
Per-endpoint rate limiting decorator.

Uses the existing Redis-backed RateLimiter to enforce endpoint-specific
rate limits keyed by tenant_id (authenticated) or client IP (public).
"""
import logging
from typing import Callable

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def rate_limit(limit: int, period: int = 60, key_func: Callable | None = None):
    """
    FastAPI dependency factory for per-endpoint rate limiting.

    Usage:
        @router.post("/listings")
        async def create_listing(
            _rl=Depends(rate_limit(20, 60)),
            current_user=Depends(get_current_user),
            ...
        ):

    Args:
        limit: Max requests allowed in the period.
        period: Time window in seconds (default 60).
        key_func: Optional callable(request) -> str for custom key.
                  Defaults to tenant_id or client IP.
    """
    refill_rate = limit / period

    async def _rate_limit_dep(request: Request):
        from listingjet.middleware.rate_limit import _bypass_for_testing
        if _bypass_for_testing:
            return

        try:
            from listingjet.services.rate_limiter import RateLimiter
            limiter = RateLimiter(
                key_prefix="endpoint",
                capacity=limit,
                refill_rate=refill_rate,
            )
        except Exception:
            logger.warning("endpoint_rate_limit.redis_unavailable path=%s", request.url.path)
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable. Please try again shortly.",
                headers={"Retry-After": "30"},
            )

        if key_func:
            key = key_func(request)
        else:
            tenant_id = getattr(request.state, "tenant_id", None)
            if tenant_id:
                from listingjet.services.tenant_bypass import is_tenant_bypassed
                if is_tenant_bypassed(tenant_id):
                    return
                key = f"tenant:{tenant_id}"
            else:
                from listingjet.middleware.rate_limit import _extract_client_ip
                key = f"ip:{_extract_client_ip(request)}"

        endpoint_key = f"{request.url.path}:{key}"

        try:
            allowed = limiter.acquire(key=endpoint_key, cost=1)
        except Exception:
            logger.warning("endpoint_rate_limit.redis_error path=%s key=%s", request.url.path, endpoint_key)
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable. Please try again shortly.",
                headers={"Retry-After": "30"},
            )

        if not allowed:
            logger.warning("endpoint_rate_limit.exceeded path=%s key=%s", request.url.path, key)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for this endpoint. Please slow down.",
                headers={"Retry-After": str(period)},
            )

    return _rate_limit_dep
