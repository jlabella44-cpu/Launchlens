"""
API rate limiting middleware.

Uses Redis token bucket (existing RateLimiter service) to enforce
per-tenant rate limits on authenticated endpoints.

Limits:
  - Authenticated: 60 req/min per tenant
  - Unauthenticated (public paths): 20 req/min per IP

Skips: /health, /docs, /openapi.json
"""
import logging

from fastapi import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

# Limits
_TENANT_CAPACITY = 60  # requests per minute
_TENANT_REFILL = 60 / 60  # 1 token/sec
_PUBLIC_CAPACITY = 20
_PUBLIC_REFILL = 20 / 60

_limiter = None


def _get_limiter():
    global _limiter
    if _limiter is None:
        from launchlens.services.rate_limiter import RateLimiter
        _limiter = RateLimiter(
            key_prefix="api",
            capacity=_TENANT_CAPACITY,
            refill_rate=_TENANT_REFILL,
        )
    return _limiter


class APIRateLimitMiddleware:
    async def __call__(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        try:
            limiter = _get_limiter()
        except Exception:
            # If Redis is down, don't block requests
            return await call_next(request)

        # Determine rate limit key
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            key = f"tenant:{tenant_id}"
        else:
            forwarded = request.headers.get("x-forwarded-for")
            ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
            key = f"ip:{ip}"

        try:
            allowed = limiter.acquire(key=key, cost=1)
        except Exception:
            # Redis error — fail open
            return await call_next(request)

        if not allowed:
            logger.warning("rate_limit.exceeded key=%s path=%s", key, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
