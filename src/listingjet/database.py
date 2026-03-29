from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from listingjet.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_recycle=300,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db(request: Request = None):
    tenant_id = getattr(request.state, "tenant_id", None) if request else None
    async with AsyncSessionLocal() as session:
        async with session.begin():
            if tenant_id:
                # SET LOCAL is transaction-scoped — parameterized query works inside BEGIN
                await session.execute(
                    text("SET LOCAL app.current_tenant = :tid"),
                    {"tid": str(tenant_id)},
                )
            yield session
