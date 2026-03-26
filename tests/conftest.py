import uuid
import asyncio
import pytest
import jwt
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from launchlens.main import app
from launchlens.database import Base, get_db
from launchlens.config import settings


TEST_DB_URL = "postgresql+asyncpg://launchlens:password@localhost:5432/launchlens_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    # CRITICAL: use Alembic (not create_all) so RLS policies and indexes are created.
    # create_all only creates tables — it skips the manual op.execute() calls in the
    # migration that enable RLS. Without this, cross-tenant isolation tests pass
    # but RLS is not actually enforced in production.
    import subprocess
    import os

    env = os.environ.copy()
    env["DATABASE_URL_SYNC"] = TEST_DB_URL.replace("+asyncpg", "")
    subprocess.run(["alembic", "upgrade", "head"], env=env, check=True)

    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield engine

    # Teardown: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
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
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


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
