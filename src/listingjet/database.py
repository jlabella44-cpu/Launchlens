from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from listingjet.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_size=50,
    max_overflow=20,
    pool_recycle=300,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db(request: Request = None):
    tenant_id = getattr(request.state, "tenant_id", None) if request else None
    async with AsyncSessionLocal() as session:
        if tenant_id:
            # SET LOCAL is transaction-scoped, so start one explicitly for it.
            # Safe: tenant_id is a validated UUID from our JWT, not user input.
            tid = str(tenant_id).replace("'", "")
            await session.execute(
                text(f"SET LOCAL app.current_tenant = '{tid}'"),
            )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
