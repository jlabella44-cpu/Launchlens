import pytest
from unittest.mock import AsyncMock, MagicMock
from launchlens.agents.content import ContentAgent
from launchlens.agents.base import AgentContext
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


def make_llm_provider(response="Beautiful 3-bedroom home with modern finishes."):
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

    assert "copy" in result
    assert len(result["copy"]) > 0
    assert result["fha_passed"] is True


@pytest.mark.asyncio
async def test_content_retries_on_fha_violation(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)

    # First call returns FHA violation, second returns clean copy
    provider = MagicMock()
    provider.complete = AsyncMock(side_effect=[
        "Perfect for families looking for a safe neighborhood.",
        "Stunning home with modern kitchen and open floor plan.",
    ])
    agent = ContentAgent(llm_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert provider.complete.call_count == 2
    assert result["fha_passed"] is True
    assert "family" not in result["copy"].lower()


@pytest.mark.asyncio
async def test_content_emits_event(db_session, listing, assets):
    from launchlens.models.outbox import Outbox
    from sqlalchemy import select

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
