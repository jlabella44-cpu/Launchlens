import uuid
import pytest
from contextlib import asynccontextmanager
from launchlens.models.listing import Listing, ListingState
from launchlens.models.asset import Asset


@asynccontextmanager
async def _wrap_session(session):
    """Wraps an existing session to look like a session factory context manager."""
    yield session


def make_session_factory(session):
    """Returns a factory that yields the given test session."""
    return lambda: _wrap_session(session)


@pytest.fixture
async def listing(db_session):
    """A listing in UPLOADING state with one tenant."""
    tenant_id = uuid.uuid4()
    obj = Listing(
        tenant_id=tenant_id,
        address={"street": "123 Main St", "city": "Austin", "state": "TX"},
        metadata_={"beds": 3, "baths": 2, "sqft": 1800},
        state=ListingState.UPLOADING,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest.fixture
async def assets(db_session, listing):
    """Three assets in 'uploaded' state for the listing."""
    result = []
    for i in range(3):
        a = Asset(
            listing_id=listing.id,
            tenant_id=listing.tenant_id,
            file_path=f"s3://bucket/listing/{listing.id}/photo_{i}.jpg",
            file_hash=f"abc{i:03d}",
            state="uploaded",
        )
        db_session.add(a)
        result.append(a)
    await db_session.flush()
    return result
