import pytest
import uuid
from launchlens.agents.coverage import CoverageAgent, REQUIRED_SHOTS
from launchlens.agents.base import AgentContext
from launchlens.models.vision_result import VisionResult
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


async def _add_vision_result(db_session, asset_id, room_label):
    vr = VisionResult(
        asset_id=asset_id,
        tier=1,
        room_label=room_label,
        is_interior=room_label != "exterior",
        quality_score=80,
        commercial_score=40,
        hero_candidate=True,
        raw_labels={},
        model_used="google-vision-v1",
    )
    db_session.add(vr)
    await db_session.flush()


@pytest.mark.asyncio
async def test_coverage_returns_missing_shots(db_session, listing, assets):
    # Only add exterior and living_room — bedroom, bathroom, kitchen are missing
    await _add_vision_result(db_session, assets[0].id, "exterior")
    await _add_vision_result(db_session, assets[1].id, "living_room")

    agent = CoverageAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert set(result["missing_shots"]) == {"kitchen", "bedroom", "bathroom"}


@pytest.mark.asyncio
async def test_coverage_returns_empty_if_all_shots_present(db_session, listing, assets):
    for asset, room in zip(assets, ["exterior", "living_room", "kitchen"]):
        await _add_vision_result(db_session, asset.id, room)
    # Add bedroom and bathroom using extra VisionResults for assets[0]
    await _add_vision_result(db_session, assets[0].id, "bedroom")
    await _add_vision_result(db_session, assets[0].id, "bathroom")

    agent = CoverageAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result["missing_shots"] == []


@pytest.mark.asyncio
async def test_coverage_missing_shots_emitted_as_event(db_session, listing, assets):
    from launchlens.models.outbox import Outbox
    await _add_vision_result(db_session, assets[0].id, "exterior")

    agent = CoverageAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    outbox_rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "coverage.gap")
    )).scalars().all()
    assert len(outbox_rows) == 1
    assert "missing_shots" in outbox_rows[0].payload
