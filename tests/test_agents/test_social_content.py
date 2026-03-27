import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from launchlens.agents.base import AgentContext
from launchlens.agents.social_content import SocialContentAgent
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState
from launchlens.models.outbox import Outbox
from launchlens.models.package_selection import PackageSelection
from launchlens.models.social_content import SocialContent
from launchlens.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory

_VALID_RESPONSE = json.dumps({
    "instagram": {
        "caption": "Welcome to 123 Main St...",
        "hashtags": ["#justlisted", "#austinrealestate", "#dreamhome"],
        "cta": "Link in bio for details"
    },
    "facebook": {
        "caption": "Just listed in Austin!...",
        "cta": "Schedule a showing today"
    }
})

_FHA_VIOLATION_RESPONSE = json.dumps({
    "instagram": {
        "caption": "Perfect for families in this safe neighborhood!",
        "hashtags": ["#justlisted", "#familyhome"],
        "cta": "Link in bio for details"
    },
    "facebook": {
        "caption": "Great schools nearby, perfect for families!",
        "cta": "Schedule a showing today"
    }
})


@pytest.fixture
async def social_listing(db_session):
    """A listing in APPROVED state with hero PackageSelection + VisionResult."""
    import uuid

    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "123 Main St", "city": "Austin", "state": "TX"},
        metadata_={"beds": 3, "baths": 2, "sqft": 1800, "price": 450000},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    asset = Asset(
        listing_id=listing.id,
        tenant_id=tenant_id,
        file_path=f"s3://bucket/listing/{listing.id}/hero.jpg",
        file_hash="hero001",
        state="uploaded",
    )
    db_session.add(asset)
    await db_session.flush()

    vr = VisionResult(
        asset_id=asset.id,
        tier=1,
        room_label="living_room",
        is_interior=True,
        quality_score=92,
        commercial_score=85,
        hero_candidate=True,
        raw_labels={"labels": [{"name": "modern_interior", "confidence": 0.95}]},
        model_used="google-vision-v1",
    )
    db_session.add(vr)
    await db_session.flush()

    ps = PackageSelection(
        listing_id=listing.id,
        tenant_id=tenant_id,
        asset_id=asset.id,
        channel="mls",
        position=0,
        selected_by="ai",
        composite_score=0.95,
    )
    db_session.add(ps)
    await db_session.flush()

    return listing


def _make_provider(response=_VALID_RESPONSE):
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=response)
    return provider


@pytest.mark.asyncio
async def test_social_content_generates_two_platforms(db_session, social_listing):
    provider = _make_provider()
    agent = SocialContentAgent(
        llm_provider=provider, session_factory=make_session_factory(db_session)
    )
    ctx = AgentContext(
        listing_id=str(social_listing.id), tenant_id=str(social_listing.tenant_id)
    )
    result = await agent.execute(ctx)

    assert result["platforms"] == ["instagram", "facebook"]
    assert result["fha_passed"] is True
    assert provider.complete.call_count == 1


@pytest.mark.asyncio
async def test_social_content_stores_in_db(db_session, social_listing):
    provider = _make_provider()
    agent = SocialContentAgent(
        llm_provider=provider, session_factory=make_session_factory(db_session)
    )
    ctx = AgentContext(
        listing_id=str(social_listing.id), tenant_id=str(social_listing.tenant_id)
    )
    await agent.execute(ctx)
    await db_session.flush()

    rows = (
        await db_session.execute(
            select(SocialContent).where(SocialContent.listing_id == social_listing.id)
        )
    ).scalars().all()
    assert len(rows) == 2
    platforms = {r.platform for r in rows}
    assert platforms == {"instagram", "facebook"}


@pytest.mark.asyncio
async def test_social_content_retries_on_fha_violation(db_session, social_listing):
    provider = MagicMock()
    provider.complete = AsyncMock(
        side_effect=[_FHA_VIOLATION_RESPONSE, _VALID_RESPONSE]
    )
    agent = SocialContentAgent(
        llm_provider=provider, session_factory=make_session_factory(db_session)
    )
    ctx = AgentContext(
        listing_id=str(social_listing.id), tenant_id=str(social_listing.tenant_id)
    )
    result = await agent.execute(ctx)

    assert provider.complete.call_count == 2
    assert result["fha_passed"] is True


@pytest.mark.asyncio
async def test_social_content_emits_event(db_session, social_listing):
    provider = _make_provider()
    agent = SocialContentAgent(
        llm_provider=provider, session_factory=make_session_factory(db_session)
    )
    ctx = AgentContext(
        listing_id=str(social_listing.id), tenant_id=str(social_listing.tenant_id)
    )
    await agent.execute(ctx)
    await db_session.flush()

    rows = (
        await db_session.execute(
            select(Outbox).where(Outbox.event_type == "social_content.completed")
        )
    ).scalars().all()
    assert len(rows) == 1
