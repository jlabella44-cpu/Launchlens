"""Tests for PerformanceIntelligenceAgent — Phase 5."""
import uuid

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.performance_intelligence import PerformanceIntelligenceAgent
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.listing_outcome import ListingOutcome
from listingjet.models.package_selection import PackageSelection
from listingjet.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory


@pytest.fixture
async def delivered_listing(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "555 Pine Rd", "city": "Portland", "state": "OR"},
        metadata_={"beds": 4, "baths": 3},
        state=ListingState.DELIVERED,
    )
    db_session.add(listing)
    await db_session.flush()
    return listing


@pytest.fixture
async def listing_with_photos(db_session, delivered_listing):
    """Delivered listing with 3 photos packaged."""
    rooms = ["exterior", "kitchen", "living_room"]
    for i, room in enumerate(rooms):
        asset = Asset(
            listing_id=delivered_listing.id,
            tenant_id=delivered_listing.tenant_id,
            file_path=f"s3://bucket/{delivered_listing.id}/photo_{i}.jpg",
            file_hash=f"hash_{i}",
            state="uploaded",
        )
        db_session.add(asset)
        await db_session.flush()

        db_session.add(VisionResult(
            asset_id=asset.id,
            tier=1,
            room_label=room,
            quality_score=75 + i * 3,
            commercial_score=70,
            hero_candidate=(i == 0),
        ))
        db_session.add(PackageSelection(
            tenant_id=delivered_listing.tenant_id,
            listing_id=delivered_listing.id,
            asset_id=asset.id,
            channel="mls",
            position=i,
            composite_score=0.8 - i * 0.05,
        ))
    await db_session.flush()
    return delivered_listing


@pytest.mark.asyncio
async def test_agent_creates_outcome_stub(db_session, listing_with_photos):
    """Agent creates an initial ListingOutcome stub for a delivered listing."""
    listing = listing_with_photos
    agent = PerformanceIntelligenceAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    result = await agent.execute(ctx)

    assert result["status"] == "completed"

    outcome = (await db_session.execute(
        select(ListingOutcome).where(ListingOutcome.listing_id == listing.id)
    )).scalar_one_or_none()

    assert outcome is not None
    assert outcome.status == "active"
    assert outcome.photo_count == 3
    assert outcome.hero_room_label == "exterior"


@pytest.mark.asyncio
async def test_agent_skips_if_outcome_exists(db_session, listing_with_photos):
    """Agent doesn't overwrite an existing outcome."""
    listing = listing_with_photos
    db_session.add(ListingOutcome(
        tenant_id=listing.tenant_id,
        listing_id=listing.id,
        status="closed",
        days_on_market=15,
        outcome_grade="A",
    ))
    await db_session.flush()

    agent = PerformanceIntelligenceAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["status"] == "completed"

    # Should still be "closed" not overwritten to "active"
    outcome = (await db_session.execute(
        select(ListingOutcome).where(ListingOutcome.listing_id == listing.id)
    )).scalar_one()
    assert outcome.status == "closed"


@pytest.mark.asyncio
async def test_agent_returns_missing_listing(db_session):
    """Agent returns skipped if listing doesn't exist."""
    fake_listing_id = str(uuid.uuid4())
    fake_tenant_id = str(uuid.uuid4())

    agent = PerformanceIntelligenceAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=fake_listing_id, tenant_id=fake_tenant_id)
    result = await agent.execute(ctx)

    assert result["status"] == "skipped"
    assert result["reason"] == "listing_not_found"
