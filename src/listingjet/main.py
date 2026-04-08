import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from listingjet.api import (
    addons,
    admin_dashboard,
    admin_listings,
    admin_tenants,
    admin_users,
    analytics,
    auth,
    billing,
    brand_kit,
    bulk,
    canva_oauth,
    cma,
    credits,
    demo,
    health,
    help_agent,
    image_edit,
    listing_permissions,
    listings_core,
    listings_media,
    listings_workflow,
    microsite,
    mls_publish,
    properties,
    sse,
    support,
    team,
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
    import redis as redis_lib

    # Initialize shared Redis connection pool — used by auth lockout,
    # credit alerts, and any future Redis consumers via get_redis() dep.
    try:
        app.state.redis = redis_lib.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        app.state.redis.ping()
    except Exception:
        logging.getLogger(__name__).warning("Redis unavailable at startup — features degraded")
        app.state.redis = None

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

    if app.state.redis:
        app.state.redis.close()


_TAG_METADATA = [
    {"name": "auth", "description": "Registration, login, and user profile"},
    {"name": "listings", "description": "Property listing CRUD, pipeline control, export"},
    {"name": "credits", "description": "Credit balance, transactions, and bundle purchases"},
    {"name": "addons", "description": "Premium add-on catalog and per-listing activation"},
    {"name": "billing", "description": "Stripe checkout, subscriptions, invoices, webhooks"},
    {"name": "brand-kit", "description": "Tenant branding configuration (colors, logo, fonts)"},
    {"name": "admin", "description": "Platform administration, tenant management, analytics"},
    {"name": "settings", "description": "Tenant settings and preferences"},
    {"name": "analytics", "description": "Usage metrics and reporting"},
    {"name": "demo", "description": "Public demo listing upload"},
    {"name": "mls", "description": "RESO Web API MLS connections and one-click publish"},
    {"name": "sse", "description": "Server-Sent Events for real-time pipeline updates"},
    {"name": "team", "description": "Team member management within a tenant"},
    {"name": "help-agent", "description": "AI help agent for product support and data lookups"},
    {"name": "support", "description": "Support tickets and customer service"},
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
        allow_origin_regex=r"https://listingjet[a-z0-9-]*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # Middleware order: security headers → request ID → rate limit → tenant auth
    # (outermost runs first, so list is reverse order)
    app.middleware("http")(TenantMiddleware())
    app.middleware("http")(APIRateLimitMiddleware())
    app.middleware("http")(RequestIDMiddleware())
    app.middleware("http")(SecurityHeadersMiddleware())
    init_monitoring(app)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(canva_oauth.router, prefix="/auth", tags=["auth"])
    app.include_router(billing.router, prefix="/billing", tags=["billing"])
    app.include_router(listing_permissions.router, prefix="/listings", tags=["listing-permissions"])
    app.include_router(listings_core.router, prefix="/listings", tags=["listings"])
    app.include_router(listings_workflow.router, prefix="/listings", tags=["listings"])
    app.include_router(listings_media.router, prefix="/listings", tags=["listings"])
    app.include_router(admin_dashboard.router, prefix="/admin", tags=["admin"])
    app.include_router(admin_tenants.router, prefix="/admin", tags=["admin"])
    app.include_router(admin_users.router, prefix="/admin", tags=["admin"])
    app.include_router(admin_listings.router, prefix="/admin", tags=["admin"])
    app.include_router(demo.router, prefix="/demo", tags=["demo"])
    app.include_router(tenant_settings.router, prefix="/settings", tags=["settings"])
    app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
    app.include_router(bulk.router, prefix="/bulk", tags=["bulk"])
    app.include_router(brand_kit.router, prefix="/brand-kit", tags=["brand-kit"])
    app.include_router(credits.router, prefix="/credits", tags=["credits"])
    app.include_router(addons.router, prefix="/addons", tags=["addons"])
    app.include_router(properties.router, prefix="/properties", tags=["properties"])
    app.include_router(cma.router, prefix="/listings", tags=["listings"])
    app.include_router(microsite.router, prefix="/listings", tags=["listings"])
    app.include_router(mls_publish.router, prefix="/listings", tags=["mls"])
    app.include_router(mls_publish.connections_router, prefix="/mls/connections", tags=["mls"])
    app.include_router(image_edit.router, prefix="/listings", tags=["image-editing"])
    app.include_router(team.router, prefix="/team", tags=["team"])
    app.include_router(sse.router, prefix="/sse", tags=["sse"])
    app.include_router(help_agent.router, prefix="/help", tags=["help-agent"])
    app.include_router(support.router, prefix="/support", tags=["support"])
    app.include_router(health.router)

    from fastapi.responses import JSONResponse

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        request_id = getattr(getattr(request, "state", None), "request_id", "unknown")
        logging.getLogger(__name__).exception(
            "unhandled_error request_id=%s", request_id,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )

    return app


app = create_app()
