import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from launchlens.api import admin, analytics, assets, auth, billing, bulk, demo, health, listings, tenant_settings
from launchlens.config import settings
from launchlens.database import AsyncSessionLocal
from launchlens.logging_config import setup_logging
from launchlens.middleware.rate_limit import APIRateLimitMiddleware
from launchlens.middleware.request_id import RequestIDMiddleware
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


_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "User registration, login, and JWT token management.",
    },
    {
        "name": "listings",
        "description": "Create and manage real estate listings through the full media pipeline — upload, compliance, review, approve, and export.",
    },
    {
        "name": "assets",
        "description": "Upload and manage listing media assets (photos, floor plans).",
    },
    {
        "name": "billing",
        "description": "Stripe-backed subscription management, checkout sessions, billing portal, and webhook event handling.",
    },
    {
        "name": "credits",
        "description": "Credit balance management — view balance, purchase bundles, and inspect transaction history.",
    },
    {
        "name": "admin",
        "description": "Platform administration — tenant management, user roles, and platform statistics. Requires admin role.",
    },
    {
        "name": "settings",
        "description": "Tenant-level configuration — webhook URL and notification preferences.",
    },
    {
        "name": "analytics",
        "description": "Usage analytics and listing performance metrics.",
    },
    {
        "name": "bulk",
        "description": "Bulk operations for processing multiple listings simultaneously.",
    },
    {
        "name": "demo",
        "description": "Demonstration endpoints for evaluating the platform without a full account.",
    },
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="LaunchLens API",
        version="1.0.0",
        description=(
            "AI-powered real estate listing media automation. "
            "From raw photos to launch-ready marketing packages in minutes."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=_OPENAPI_TAGS,
        lifespan=lifespan,
    )
    # Middleware order: request ID → rate limit → tenant auth
    # (outermost runs first, so list is reverse order)
    app.middleware("http")(TenantMiddleware())
    app.middleware("http")(APIRateLimitMiddleware())
    app.middleware("http")(RequestIDMiddleware())
    init_monitoring(app)

    # Versioned routes — canonical API surface
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
    app.include_router(listings.router, prefix="/api/v1/listings", tags=["listings"])
    app.include_router(assets.router, prefix="/api/v1/assets", tags=["assets"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(demo.router, prefix="/api/v1/demo", tags=["demo"])
    app.include_router(tenant_settings.router, prefix="/api/v1/settings", tags=["settings"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    app.include_router(bulk.router, prefix="/api/v1/bulk", tags=["bulk"])

    # Legacy unversioned routes — kept for backwards compatibility, hidden from docs
    app.include_router(auth.router, prefix="/auth", tags=["auth"], include_in_schema=False)
    app.include_router(billing.router, prefix="/billing", tags=["billing"], include_in_schema=False)
    app.include_router(listings.router, prefix="/listings", tags=["listings"], include_in_schema=False)
    app.include_router(assets.router, prefix="/assets", tags=["assets"], include_in_schema=False)
    app.include_router(admin.router, prefix="/admin", tags=["admin"], include_in_schema=False)
    app.include_router(demo.router, prefix="/demo", tags=["demo"], include_in_schema=False)
    app.include_router(tenant_settings.router, prefix="/settings", tags=["settings"], include_in_schema=False)
    app.include_router(analytics.router, prefix="/analytics", tags=["analytics"], include_in_schema=False)
    app.include_router(bulk.router, prefix="/bulk", tags=["bulk"], include_in_schema=False)

    app.include_router(health.router)

    return app


app = create_app()
