import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from listingjet.api import (
    addons,
    admin,
    analytics,
    assets,
    auth,
    billing,
    brand_kit,
    bulk,
    credits,
    demo,
    health,
    listings,
    sse,
    tenant_settings,
)
from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.logging_config import setup_logging
from listingjet.middleware.rate_limit import APIRateLimitMiddleware
from listingjet.middleware.request_id import RequestIDMiddleware
from listingjet.middleware.security_headers import SecurityHeadersMiddleware
from listingjet.middleware.tenant import TenantMiddleware
from listingjet.monitoring import init_monitoring
from listingjet.services.outbox_poller import OutboxPoller

setup_logging(app_env=settings.app_env, log_level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    try:
        poller = OutboxPoller(session_factory=AsyncSessionLocal)
        task = asyncio.create_task(poller.run())
    except Exception:
        logging.getLogger(__name__).warning("Outbox poller failed to start — running without it")

    yield

    if task:
        try:
            poller.stop()
            task.cancel()
            await task
        except (asyncio.CancelledError, Exception):
            pass


_TAG_METADATA = [
    {"name": "auth", "description": "Registration, login, and user profile"},
    {"name": "listings", "description": "Property listing CRUD, pipeline control, export"},
    {"name": "credits", "description": "Credit balance, transactions, and bundle purchases"},
    {"name": "addons", "description": "Premium add-on catalog and per-listing activation"},
    {"name": "billing", "description": "Stripe checkout, subscriptions, invoices, webhooks"},
    {"name": "brand-kit", "description": "Tenant branding configuration (colors, logo, fonts)"},
    {"name": "admin", "description": "Platform administration, tenant management, analytics"},
    {"name": "assets", "description": "Photo asset management"},
    {"name": "settings", "description": "Tenant settings and preferences"},
    {"name": "analytics", "description": "Usage metrics and reporting"},
    {"name": "demo", "description": "Public demo listing upload"},
    {"name": "sse", "description": "Server-Sent Events for real-time pipeline updates"},
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="ListingJet API",
        version="1.0.0",
        description=(
            "AI-powered real estate listing media automation. "
            "Upload property photos, get MLS bundles, branded flyers, "
            "AI descriptions, social content, video tours, and 3D floorplans."
        ),
        lifespan=lifespan,
        openapi_tags=_TAG_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    # CORS — must be added before other middleware so OPTIONS preflight works
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
    app.include_router(credits.router, prefix="/credits", tags=["credits"])
    app.include_router(addons.router, prefix="/addons", tags=["addons"])
    app.include_router(sse.router, tags=["sse"])
    app.include_router(health.router)

    # Debug error handler — returns tracebacks in response (remove for real production)
    import traceback as tb

    from fastapi.responses import JSONResponse

    @app.exception_handler(Exception)
    async def debug_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": tb.format_exc()},
        )

    return app


app = create_app()
