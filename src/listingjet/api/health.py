"""Health check endpoints."""

import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis
import sqlalchemy
from fastapi import APIRouter
from starlette.responses import JSONResponse

from listingjet.config import settings
from listingjet.database import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic health check — tests DB connectivity."""
    checks = {"api": "ok"}

    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}


@router.get("/health/deep")
async def deep_health():
    """Deep health check — verifies DB, Redis, and Temporal connectivity."""
    components = {}

    # Database
    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        components["database"] = "ok"
    except Exception as e:
        logger.warning("Health check: database failed: %s", e)
        components["database"] = f"error: {e}"

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        components["redis"] = "ok"
    except Exception as e:
        logger.warning("Health check: redis failed: %s", e)
        components["redis"] = f"error: {e}"

    # Worker
    from listingjet.pipeline.runner import WORKER_STATE
    if settings.worker_enabled:
        tick = WORKER_STATE.get("last_tick")
        fresh = tick is not None and (datetime.now(timezone.utc) - tick).total_seconds() < 60
        components["worker"] = "ok" if fresh else "error: no tick in 60s"
    else:
        components["worker"] = "external"

    all_ok = all(v == "ok" for v in components.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if all_ok else "degraded", **components},
    )
