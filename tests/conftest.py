import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from listingjet.api.deps import get_db_admin
from listingjet.config import settings
from listingjet.database import Base, get_db
from listingjet.main import app

TEST_DB_URL = "postgresql+asyncpg://listingjet:password@localhost:5433/listingjet_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _mock_external_services():
    """Bypass all external services in tests: Redis, Temporal, rate limiters.

    Without this:
    - Redis calls block for 2s each (socket timeout) or hang indefinitely
    - Temporal Client.connect() hangs for 60s+ trying to reach localhost:7233
    - Rate limiter middleware returns 429 on every request
    """
    import listingjet.middleware.rate_limit as rl_mod
    rl_mod._bypass_for_testing = True

    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.ttl.return_value = 900
    mock_redis.pipeline.return_value = MagicMock(
        __enter__=MagicMock(return_value=MagicMock(
            incr=MagicMock(), expire=MagicMock(), execute=MagicMock()
        )),
        __exit__=MagicMock(return_value=False),
    )

    # Mock Temporal client so it never tries to connect to localhost:7233
    mock_temporal = MagicMock()
    mock_temporal.start_pipeline = AsyncMock(return_value="mock-workflow-id")
    mock_temporal.signal_review_completed = AsyncMock()

    with (
        patch("listingjet.services.rate_limiter.RateLimiter", return_value=mock_redis),
        patch("listingjet.api.auth._get_lockout_redis", return_value=mock_redis),
        patch("listingjet.services.credits._get_redis", return_value=mock_redis),
        patch("listingjet.temporal_client.get_temporal_client", return_value=mock_temporal),
        patch("listingjet.api.listings_draft.get_temporal_client", return_value=mock_temporal),
        patch("listingjet.api.listings_media.get_temporal_client", return_value=mock_temporal),
        patch("listingjet.api.listings_workflow.get_temporal_client", return_value=mock_temporal),
        patch("listingjet.api.bulk.get_temporal_client", return_value=mock_temporal),
    ):
        yield

    rl_mod._bypass_for_testing = False


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

    # Find alembic binary: try standard locations, then fall back to shutil.which,
    # then fall back to running as a Python module.
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
        # Re-insert seed data that migrations provide (034, 038, 039)
        await conn.execute(
            Base.metadata.tables["addon_catalog"].insert(),
            [
                {"slug": "virtual_staging", "name": "Virtual Staging", "credit_cost": 15, "is_active": True, "metadata": {"styles": ["modern", "contemporary", "minimalist"]}},
                {"slug": "image_editing", "name": "AI Image Editing", "credit_cost": 5, "is_active": True, "metadata": {"capabilities": ["remove_object", "enhance"]}},
                {"slug": "cma_report", "name": "CMA Report", "credit_cost": 10, "is_active": True, "metadata": {"format": "html"}},
                {"slug": "ai_video_tour", "name": "AI Video Tour", "credit_cost": 20, "is_active": True, "metadata": {}},
                {"slug": "3d_floorplan", "name": "3D Floorplan", "credit_cost": 8, "is_active": True, "metadata": {}},
                {"slug": "all_addons_bundle", "name": "All Add-ons Bundle", "credit_cost": 30, "is_active": True, "metadata": {"includes": ["ai_video_tour", "virtual_staging", "3d_floorplan"]}},
            ],
        )
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()  # isolate each test


def make_jwt(tenant_id: str, user_id: str | None = None) -> str:
    uid = user_id or str(uuid.uuid4())
    return jwt.encode(
        {"tenant_id": tenant_id, "sub": uid, "role": "admin", "type": "access"},
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

    import listingjet.api.health as health_module
    original_engine = health_module.engine
    health_module.engine = test_engine

    # Mock credit deduction to always succeed (tests don't need real credit enforcement)
    # Rate limiting + Redis are handled by the autouse _mock_redis_globally fixture.
    async def _noop_deduct(*args, **kwargs):
        import uuid as _uuid
        mock_txn = MagicMock(amount=1)
        mock_txn.id = _uuid.uuid4()
        return mock_txn

    with patch("listingjet.services.credits.CreditService.deduct_credits", side_effect=_noop_deduct):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client

    health_module.engine = original_engine
    app.dependency_overrides.clear()


async def promote_to_superadmin(client: AsyncClient, token: str):
    """Promote a registered user to SUPERADMIN by directly updating the DB via internal endpoint."""
    import jwt as pyjwt
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    user_id = payload["sub"]
    # Direct DB update via the test engine
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    engine = create_async_engine(TEST_DB_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("UPDATE users SET role = 'superadmin' WHERE id = :uid"),
                {"uid": user_id},
            )
    await engine.dispose()


@pytest.fixture
async def two_tenants(async_client, db_session):
    """Creates two tenants and a listing belonging to tenant B."""
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    # Create a listing for tenant_b directly in DB
    from listingjet.models.listing import Listing, ListingState

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
