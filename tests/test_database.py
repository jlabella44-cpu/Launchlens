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
