"""
API rate limiting middleware.

Uses Redis token bucket (RateLimiter service) to enforce per-tenant rate
limits.  All state lives in Redis — no Python-side singletons — so limits
are shared correctly across all Uvicorn worker processes.

Limits:
  - Authenticated: 60 req/min per tenant
  - Unauthenticated (public paths): 20 req/min per IP

Skips: /health, /docs, /openapi.json

IP extraction: Only trusts X-Forwarded-For when TRUSTED_PROXY_COUNT > 0.
"""
import logging

from fastapi import Request
from starlette.responses import JSONResponse

from listingjet.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Number of trusted reverse proxies in front of the app.
# 0 = direct connection (ignore X-Forwarded-For entirely).
# 1 = single proxy (use rightmost-1 entry in X-Forwarded-For).
TRUSTED_PROXY_COUNT: int = 0

_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

# Limits
_TENANT_CAPACITY = 60  # requests per minute
_TENANT_REFILL = 60 / 60  # 1 token/sec
_PUBLIC_CAPACITY = 20
_PUBLIC_REFILL = 20 / 60


def _extract_client_ip(request: Request) -> str:
    """Extract client IP, only trusting X-Forwarded-For when behind known proxies."""
    if TRUSTED_PROXY_COUNT > 0:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",")]
            # Use the entry at position -(TRUSTED_PROXY_COUNT) from the right
            idx = max(0, len(parts) - TRUSTED_PROXY_COUNT)
            return parts[idx]
    return request.client.host if request.client else "unknown"


# Module-level reference so tests can replace _limiter without walking the
# ASGI middleware stack.  Set by __init__, patched by conftest.
_active_middleware: "APIRateLimitMiddleware | None" = None

# Set to True in tests to bypass rate limiting entirely.
_bypass_for_testing: bool = False


class APIRateLimitMiddleware:
    """Rate-limit middleware.  One RateLimiter instance per *process* is fine
    because the actual token-bucket state lives in Redis, not in Python
    memory.  The instance is created once at startup (not lazily) so there
    is no check-and-set race between concurrent async tasks.
    """

    def __init__(self):
        global _active_middleware
        try:
            self._limiter = RateLimiter(
                key_prefix="api",
                capacity=_TENANT_CAPACITY,
                refill_rate=_TENANT_REFILL,
            )
        except Exception:
            logger.warning("Redis unavailable at startup — rate limiting disabled")
            self._limiter = None
        _active_middleware = self

    async def __call__(self, request: Request, call_next):
        if _bypass_for_testing or request.url.path in _SKIP_PATHS:
            return await call_next(request)

        if self._limiter is None:
            logger.warning("rate_limit.redis_unavailable — denying request path=%s", request.url.path)
            return JSONResponse(
                status_code=503,
                content={"detail": "Service temporarily unavailable. Please try again shortly."},
                headers={"Retry-After": "30"},
            )

        # Determine rate limit key
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            key = f"tenant:{tenant_id}"
        else:
            ip = _extract_client_ip(request)
            key = f"ip:{ip}"

        try:
            allowed = self._limiter.acquire(key=key, cost=1)
        except Exception:
            logger.warning("rate_limit.redis_error — denying request path=%s", request.url.path)
            return JSONResponse(
                status_code=503,
                content={"detail": "Service temporarily unavailable. Please try again shortly."},
                headers={"Retry-After": "30"},
            )

        capacity = _TENANT_CAPACITY if tenant_id else _PUBLIC_CAPACITY

        if not allowed:
            logger.warning("rate_limit.exceeded key=%s path=%s", key, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(capacity),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(capacity)
        return response
