import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.database import get_db


@pytest.mark.asyncio
async def test_get_db_yields_session():
    # Runs after conftest.py is in place (Task 11)
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break
