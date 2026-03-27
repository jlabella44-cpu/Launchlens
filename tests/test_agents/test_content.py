from unittest.mock import AsyncMock, MagicMock

import pytest

from launchlens.agents.base import AgentContext
from launchlens.agents.content import ContentAgent
from launchlens.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory


async def _add_vr(db_session, asset_id, room_label="living_room", quality=80):
    vr = VisionResult(
        asset_id=asset_id, tier=1, room_label=room_label,
        is_interior=True, quality_score=quality, commercial_score=60,
        hero_candidate=True, raw_labels={"labels": [{"name": "hardwood", "confidence": 0.9}]},
        model_used="google-vision-v1",
    )
    db_session.add(vr)
    await db_session.flush()


def make_llm_provider(response='{"mls_safe": "Spacious 3-bedroom home.", "marketing": "Beautiful 3-bedroom home with modern finishes."}'):
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=response)
    return provider


@pytest.mark.asyncio
async def test_content_returns_copy(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)

    provider = make_llm_provider()
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert "mls_safe" in result
    assert "marketing" in result
    assert len(result["mls_safe"]) > 0
    assert len(result["marketing"]) > 0
    assert result["fha_passed"] is True


@pytest.mark.asyncio
async def test_content_retries_on_fha_violation(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)

    # First call returns FHA violation, second returns clean copy
    provider = MagicMock()
    fha_violation = '{"mls_safe": "Perfect for families in a safe neighborhood.", "marketing": "Great for families looking for safe neighborhoods."}'
    clean = '{"mls_safe": "Spacious 3-bedroom home.", "marketing": "Stunning home with modern kitchen and open floor plan."}'
    provider.complete = AsyncMock(side_effect=[fha_violation, clean])
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert provider.complete.call_count == 2
    assert result["fha_passed"] is True
    assert "family" not in result["mls_safe"].lower()
    assert "family" not in result["marketing"].lower()


@pytest.mark.asyncio
async def test_content_emits_event(db_session, listing, assets):
    from sqlalchemy import select

    from launchlens.models.outbox import Outbox

    for a in assets:
        await _add_vr(db_session, a.id)

    provider = make_llm_provider()
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "content.completed")
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_content_returns_dual_tone(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)
    response = '{"mls_safe": "Spacious 3-bedroom home with 2 bathrooms.", "marketing": "Welcome home to this stunning 3-bedroom retreat with modern finishes and natural light."}'
    provider = make_llm_provider(response)
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert "mls_safe" in result
    assert "marketing" in result
    assert len(result["mls_safe"]) > 0
    assert len(result["marketing"]) > 0
    assert result["fha_passed"] is True
