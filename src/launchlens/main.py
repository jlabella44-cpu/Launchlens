from fastapi import FastAPI
from launchlens.middleware.tenant import TenantMiddleware
from launchlens.api import listings, assets, admin


def create_app() -> FastAPI:
    app = FastAPI(title="LaunchLens", version="0.1.0")
    app.middleware("http")(TenantMiddleware())
    app.include_router(listings.router, prefix="/listings", tags=["listings"])
    app.include_router(assets.router, prefix="/assets", tags=["assets"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
