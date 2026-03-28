import asyncio
import uuid
from unittest.mock import MagicMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from launchlens.api.deps import get_db_admin
from launchlens.config import settings
from launchlens.database import Base, get_db
from launchlens.main import app

TEST_DB_URL = "postgresql+asyncpg://launchlens:password@localhost:5433/launchlens_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _mock_rate_limiter_global():
    """Bypass Redis-backed rate limiter in all tests (Redis not available in CI)."""
    mock_limiter = MagicMock()
    mock_limiter.acquire.return_value = True
    with patch("launchlens.middleware.rate_limit._get_limiter", return_value=mock_limiter):
        yield


@pytest.fixture(scope="session")
async def test_engine():
    # CRITICAL: use Alembic (not create_all) so RLS policies and indexes are created.
    # create_all only creates tables — it skips the manual op.execute() calls in the
    # migration that enable RLS. Without this, cross-tenant isolation tests pass
    # but RLS is not actually enforced in production.
    import os
    import shutil
    import subprocess
    import sys

    alembic_exe = os.path.join(os.path.dirname(sys.executable), "Scripts", "alembic.exe")
    if not os.path.exists(alembic_exe):
        alembic_exe = os.path.join(os.path.dirname(sys.executable), "alembic")
    if not os.path.exists(alembic_exe):
        found = shutil.which("alembic")
        alembic_exe = found if found else None

    env = os.environ.copy()
    env["DATABASE_URL_SYNC"] = TEST_DB_URL.replace("+asyncpg", "")
    if alembic_exe:
        subprocess.run([alembic_exe, "upgrade", "head"], env=env, check=True)
    else:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True,
        )

    from sqlalchemy.pool import NullPool
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    yield engine

    # Teardown: truncate all data but keep schema so re-runs work without re-migrating
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()  # isolate each test


def make_jwt(tenant_id: str) -> str:
    return jwt.encode(
        {"tenant_id": tenant_id, "sub": f"user-{tenant_id}"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@pytest.fixture
def tenant_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def tenant_auth_headers(tenant_id: str) -> dict:
    return {"Authorization": f"Bearer {make_jwt(tenant_id)}"}


@pytest.fixture
async def async_client(test_engine):
    from sqlalchemy import text

    _test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db(request=None):
        tenant_id = getattr(request.state, "tenant_id", None) if request else None
        async with _test_session_factory() as session:
            if tenant_id:
                await session.execute(
                    text("SET LOCAL app.current_tenant = :tid"),
                    {"tid": str(tenant_id)},
                )
            yield session

    async def override_get_db_admin():
        async with _test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_admin] = override_get_db_admin

    import launchlens.api.health as health_module
    original_engine = health_module.engine
    health_module.engine = test_engine

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    health_module.engine = original_engine
    app.dependency_overrides.clear()


@pytest.fixture
async def two_tenants(async_client, db_session):
    """Creates two tenants and a listing belonging to tenant B."""
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    # Create a listing for tenant_b directly in DB
    from launchlens.models.listing import Listing, ListingState

    listing = Listing(
        tenant_id=tenant_b,
        address={"street": "123 Main St", "city": "Denver", "state": "CO", "zip": "80201"},
        metadata_={"beds": 3, "baths": 2, "sqft": 1800, "price": 500000},
        state=ListingState.NEW,
    )
    db_session.add(listing)
    await db_session.commit()
    return (
        {"Authorization": f"Bearer {make_jwt(tenant_a)}"},
        {"Authorization": f"Bearer {make_jwt(tenant_b)}"},
        str(listing.id),
    )
