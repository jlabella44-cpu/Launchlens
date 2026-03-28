from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from launchlens.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db(request: Request = None):
    tenant_id = getattr(request.state, "tenant_id", None) if request else None
    async with AsyncSessionLocal() as session:
        if tenant_id:
            # CRITICAL: SET LOCAL is transaction-scoped — auto-reset on COMMIT/ROLLBACK
            # Never use SET (session-scoped) — leaks across pooled connections
            await session.execute(
                text("SET LOCAL app.current_tenant = :tid"),
                {"tid": str(tenant_id)},
            )
        yield session
