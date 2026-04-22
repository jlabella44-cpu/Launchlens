"""Redis-backed cache of the per-tenant rate-limit bypass flag.

The admin endpoint is the only writer; the rate-limit middleware and
per-endpoint decorator read via ``is_tenant_bypassed``. The DB column
``tenants.bypass_limits`` is the source of truth — Redis is purely a
cache so the middleware can skip the token bucket without a DB round
trip. A Redis flush falls back to "no bypass" (fail-safe off); admins
re-toggle to restore.
"""
import logging

import redis as redis_lib

logger = logging.getLogger(__name__)

_KEY_FMT = "tenant_bypass:{tid}"


def _get_redis():
    from listingjet.config import settings
    return redis_lib.from_url(
        settings.redis_url, socket_connect_timeout=2, socket_timeout=2
    )


def set_tenant_bypass(tenant_id: str, enabled: bool) -> None:
    """Write or clear the bypass flag for a tenant. Best-effort."""
    try:
        r = _get_redis()
        key = _KEY_FMT.format(tid=tenant_id)
        if enabled:
            r.set(key, "1")
        else:
            r.delete(key)
    except Exception:
        logger.warning(
            "tenant_bypass.redis_write_failed tenant=%s enabled=%s",
            tenant_id, enabled,
        )


def is_tenant_bypassed(tenant_id: str) -> bool:
    """Return True if the tenant's bypass flag is set in Redis."""
    try:
        r = _get_redis()
        return bool(r.exists(_KEY_FMT.format(tid=tenant_id)))
    except Exception:
        return False
