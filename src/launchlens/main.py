import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from launchlens.api import (
    admin,
    analytics,
    assets,
    auth,
    billing,
    brand_kit,
    bulk,
    demo,
    health,
    listings,
    sse,
    tenant_settings,
)
from launchlens.config import settings
from launchlens.database import AsyncSessionLocal
from launchlens.logging_config import setup_logging
from launchlens.middleware.rate_limit import APIRateLimitMiddleware
from launchlens.middleware.request_id import RequestIDMiddleware
from launchlens.middleware.security_headers import SecurityHeadersMiddleware
from launchlens.middleware.tenant import TenantMiddleware
from launchlens.monitoring import init_monitoring
from launchlens.services.outbox_poller import OutboxPoller

setup_logging(app_env=settings.app_env, log_level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    poller = OutboxPoller(session_factory=AsyncSessionLocal)
    task = asyncio.create_task(poller.run())
    yield
    poller.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="LaunchLens",
        version="0.9.4",
        description="The Listing Media OS — from raw photos to launch-ready marketing in minutes.",
        lifespan=lifespan,
    )
    # Middleware order: security headers → request ID → rate limit → tenant auth
    # (outermost runs first, so list is reverse order)
    app.middleware("http")(TenantMiddleware())
    app.middleware("http")(APIRateLimitMiddleware())
    app.middleware("http")(RequestIDMiddleware())
    app.middleware("http")(SecurityHeadersMiddleware())
    init_monitoring(app)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(billing.router, prefix="/billing", tags=["billing"])
    app.include_router(listings.router, prefix="/listings", tags=["listings"])
    app.include_router(assets.router, prefix="/assets", tags=["assets"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(demo.router, prefix="/demo", tags=["demo"])
    app.include_router(tenant_settings.router, prefix="/settings", tags=["settings"])
    app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
    app.include_router(bulk.router, prefix="/bulk", tags=["bulk"])
    app.include_router(brand_kit.router, prefix="/brand-kit", tags=["brand-kit"])
    app.include_router(sse.router, tags=["sse"])
    app.include_router(health.router)

    return app


app = create_app()
