import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.database import get_db


@pytest.mark.asyncio
async def test_get_db_yields_session():
    # Runs after conftest.py is in place (Task 11)
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break


def test_latest_rls_migration_allows_admin_context():
    migration_path = "alembic/versions/051_admin_rls_bypass.py"
    from pathlib import Path

    content = Path(migration_path).read_text()

    assert "app.is_admin" in content
    assert "DROP POLICY IF EXISTS tenant_isolation" in content
    assert "CREATE POLICY tenant_isolation" in content


@pytest.mark.asyncio
async def test_get_db_resets_current_tenant_on_every_transaction(monkeypatch):
    """`SET LOCAL app.current_tenant` is transaction-scoped and would be
    cleared by any mid-request `db.commit()`. The dependency must hook
    `after_begin` so the flag is re-set on every transaction the session
    opens. Mirrors the get_db_admin guarantee."""
    import uuid as _uuid
    from types import SimpleNamespace

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from listingjet import database as db_mod

    sync_engine = create_engine("sqlite://")
    real_sync_session = Session(bind=sync_engine)
    tenant_id = _uuid.uuid4()

    class FakeAsyncSession:
        def __init__(self):
            self.sync_session = real_sync_session

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def commit(self):
            pass

        async def rollback(self):
            pass

    monkeypatch.setattr(db_mod, "AsyncSessionLocal", lambda: FakeAsyncSession())

    request = SimpleNamespace(state=SimpleNamespace(tenant_id=tenant_id))

    listeners_before = list(real_sync_session.dispatch.after_begin)

    gen = db_mod.get_db(request=request)
    session = await gen.__anext__()

    listeners_during = list(session.sync_session.dispatch.after_begin)
    new_listeners = [lst for lst in listeners_during if lst not in listeners_before]
    assert len(new_listeners) == 1, "get_db must register exactly one after_begin listener"
    listener = new_listeners[0]

    executed: list[str] = []

    class FakeConn:
        def execute(self, stmt):
            executed.append(str(stmt))

    listener(session.sync_session, None, FakeConn())
    listener(session.sync_session, None, FakeConn())

    assert len(executed) == 2
    expected = f"SET LOCAL app.current_tenant = '{tenant_id}'"
    assert all(expected in s for s in executed)

    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass

    remaining = list(session.sync_session.dispatch.after_begin)
    assert listener not in remaining, "listener must be removed on session teardown"
