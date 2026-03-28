"""Health check endpoints."""

import logging

import redis.asyncio as aioredis
import sqlalchemy
from fastapi import APIRouter
from starlette.responses import JSONResponse

from launchlens.config import settings
from launchlens.database import engine

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

    # Temporal
    try:
        from temporalio.client import Client
        client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
        await client.service_client.check_health()
        components["temporal"] = "ok"
    except Exception as e:
        logger.warning("Health check: temporal failed: %s", e)
        components["temporal"] = f"error: {e}"

    all_ok = all(v == "ok" for v in components.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if all_ok else "degraded", **components},
    )
