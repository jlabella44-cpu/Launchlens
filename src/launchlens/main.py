import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from launchlens.api import admin, assets, auth, billing, demo, listings
from launchlens.database import AsyncSessionLocal
from launchlens.middleware.tenant import TenantMiddleware
from launchlens.services.outbox_poller import OutboxPoller


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
    app = FastAPI(title="LaunchLens", version="0.1.0", lifespan=lifespan)
    app.middleware("http")(TenantMiddleware())
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(billing.router, prefix="/billing", tags=["billing"])
    app.include_router(listings.router, prefix="/listings", tags=["listings"])
    app.include_router(assets.router, prefix="/assets", tags=["assets"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(demo.router, prefix="/demo", tags=["demo"])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
