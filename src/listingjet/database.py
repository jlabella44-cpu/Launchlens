from fastapi import Request
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from listingjet.config import settings

# When PgBouncer is enabled (transaction-pool mode), asyncpg's prepared-
# statement cache must be disabled because PgBouncer may route successive
# queries to different server connections where the statements don't exist.
_connect_args: dict = {}
if settings.db_use_pgbouncer:
    _connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args=_connect_args,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db(request: Request = None):
    tenant_id = getattr(request.state, "tenant_id", None) if request else None
    async with AsyncSessionLocal() as session:
        listener = None
        if tenant_id:
            # SET LOCAL is transaction-scoped, so any mid-request `db.commit()`
            # would clear `app.current_tenant` and let RLS filter subsequent
            # reads to zero rows. Re-set the flag on every transaction the
            # session opens via `after_begin`. Safe: tenant_id is a validated
            # UUID from our JWT, not user input.
            tid = str(tenant_id).replace("'", "")

            @event.listens_for(session.sync_session, "after_begin")
            def _set_current_tenant(_session, _transaction, connection):
                connection.execute(text(f"SET LOCAL app.current_tenant = '{tid}'"))

            listener = _set_current_tenant
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            if listener is not None:
                event.remove(session.sync_session, "after_begin", listener)
