# tests/test_agents/test_photo_analysis.py
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.photo_analysis import (
    Compliance,
    PhotoAnalysis,
    PhotoAnalysisAgent,
    RoomLabel,
)
from listingjet.models.event import Event
from listingjet.models.vision_result import VisionResult
from listingjet.providers.mock import MockClaudeClient
from tests.test_agents.conftest import make_session_factory


@pytest.fixture(autouse=True)
def patch_storage():
    storage = MagicMock()
    storage.presigned_url.side_effect = lambda key, **kw: f"https://mock/{key}"
    with patch("listingjet.agents.photo_analysis.get_storage", return_value=storage):
        yield storage


def _url(asset) -> str:
    return f"https://mock/{asset.proxy_path or asset.file_path}"


def _analysis(**kw) -> PhotoAnalysis:
    base = dict(
        room=RoomLabel.living_room,
        is_interior=True,
        is_photo=True,
        quality=80,
        hero_score=50,
        features=[],
        is_empty_room=False,
        compliance=Compliance(people=False, signage=False, branding=False, text_overlay=False),
        notes="",
    )
    base.update(kw)
    return PhotoAnalysis(**base)


def _three_analyses():
    """An exterior hero, an empty bedroom, and a screenshot with text."""
    return [
        _analysis(
            room=RoomLabel.exterior, is_interior=False, quality=92, hero_score=88,
            features=["curb appeal", "landscaping"], notes="Bright front elevation.",
        ),
        _analysis(
            room=RoomLabel.bedroom, quality=70, hero_score=40, is_empty_room=True,
            notes="Unfurnished bedroom.",
        ),
        _analysis(
            room=RoomLabel.screenshot, is_interior=False, is_photo=False, quality=20,
            hero_score=5, notes="Screenshot with overlaid contact info.",
            compliance=Compliance(people=False, signage=False, branding=False, text_overlay=True),
        ),
    ]


def _client_for(assets, analyses) -> MockClaudeClient:
    client = MockClaudeClient()
    client.by_url = {_url(a): an for a, an in zip(assets, analyses, strict=True)}
    return client


async def _ingested(db_session, assets):
    for a in assets:
        a.state = "ingested"
    await db_session.flush()


@pytest.mark.asyncio
async def test_writes_one_vision_result_per_asset_with_mapped_columns(db_session, listing, assets):
    await _ingested(db_session, assets)
    analyses = _three_analyses()
    agent = PhotoAnalysisAgent(
        claude=_client_for(assets, analyses),
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result == {"analyzed": 3, "failed": 0, "flagged": 1}

    rows = (await db_session.execute(select(VisionResult))).scalars().all()
    assert len(rows) == 3
    assert all(r.tier == 1 for r in rows)
    by_asset = {r.asset_id: r for r in rows}

    hero = by_asset[assets[0].id]
    assert hero.room_label == "exterior"
    assert hero.is_interior is False
    assert hero.quality_score == 92
    assert hero.commercial_score == 88
    assert hero.hero_score == 88
    assert hero.hero_candidate is True
    assert hero.hero_explanation == "Bright front elevation."
    assert hero.is_photo is True
    assert hero.is_empty_room is False
    assert hero.features == ["curb appeal", "landscaping"]
    assert hero.compliance == {
        "people": False, "signage": False, "branding": False, "text_overlay": False,
    }
    assert hero.raw_labels["room"] == "exterior"
    assert hero.model_used  # the configured Claude fast model

    bedroom = by_asset[assets[1].id]
    assert bedroom.hero_candidate is False  # hero_score 40 < 70
    assert bedroom.is_empty_room is True

    shot = by_asset[assets[2].id]
    assert shot.is_photo is False
    assert shot.compliance["text_overlay"] is True


@pytest.mark.asyncio
async def test_replaces_existing_vision_results_for_the_asset(db_session, listing, assets):
    await _ingested(db_session, assets)
    stale = VisionResult(asset_id=assets[0].id, tier=1, room_label="kitchen", model_used="old")
    stale_t2 = VisionResult(asset_id=assets[0].id, tier=2, room_label="kitchen", model_used="old")
    db_session.add_all([stale, stale_t2])
    await db_session.flush()

    agent = PhotoAnalysisAgent(
        claude=_client_for(assets, _three_analyses()),
        session_factory=make_session_factory(db_session),
    )
    await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id)))

    rows = (await db_session.execute(
        select(VisionResult).where(VisionResult.asset_id == assets[0].id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].room_label == "exterior"


@pytest.mark.asyncio
async def test_emits_backward_compatible_events(db_session, listing, assets):
    await _ingested(db_session, assets)
    agent = PhotoAnalysisAgent(
        claude=_client_for(assets, _three_analyses()),
        session_factory=make_session_factory(db_session),
    )
    await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id)))

    events = (await db_session.execute(
        select(Event).where(Event.listing_id == listing.id)
    )).scalars().all()
    by_type = {e.event_type: e.payload for e in events}

    assert by_type["photo_analysis.completed"] == {"analyzed": 3, "failed": 0, "flagged": 1}
    report = by_type["photo_compliance.completed"]
    assert report["total_photos"] == 3
    assert report["flagged_count"] == 1
    assert report["all_compliant"] is False


@pytest.mark.asyncio
async def test_one_failing_asset_still_persists_the_others(db_session, listing, assets):
    await _ingested(db_session, assets)
    client = _client_for(assets, _three_analyses())
    bad_url = _url(assets[2])
    inner = client.analyze_images

    async def flaky(image_urls, prompt, schema, **kw):
        if image_urls[0] == bad_url:
            raise RuntimeError("claude exploded")
        return await inner(image_urls, prompt, schema, **kw)

    client.analyze_images = flaky

    agent = PhotoAnalysisAgent(claude=client, session_factory=make_session_factory(db_session))
    result = await agent.execute(
        AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    )

    assert result == {"analyzed": 2, "failed": 1, "flagged": 0}
    rows = (await db_session.execute(select(VisionResult))).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_all_failing_raises_after_persisting(db_session, listing, assets):
    await _ingested(db_session, assets)
    client = MockClaudeClient()

    async def always_fail(image_urls, prompt, schema, **kw):
        raise RuntimeError("claude down")

    client.analyze_images = always_fail

    agent = PhotoAnalysisAgent(claude=client, session_factory=make_session_factory(db_session))
    with pytest.raises(RuntimeError, match="photo_analysis: 3 of 3 photos failed"):
        await agent.execute(
            AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
        )

    rows = (await db_session.execute(select(VisionResult))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_majority_failing_raises_but_keeps_successes(db_session, listing, assets):
    await _ingested(db_session, assets)
    client = _client_for(assets, _three_analyses())
    ok_url = _url(assets[0])
    inner = client.analyze_images

    async def mostly_fail(image_urls, prompt, schema, **kw):
        if image_urls[0] != ok_url:
            raise RuntimeError("claude flaked")
        return await inner(image_urls, prompt, schema, **kw)

    client.analyze_images = mostly_fail

    agent = PhotoAnalysisAgent(claude=client, session_factory=make_session_factory(db_session))
    with pytest.raises(RuntimeError, match="photo_analysis: 2 of 3 photos failed"):
        await agent.execute(
            AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
        )

    rows = (await db_session.execute(select(VisionResult))).scalars().all()
    assert len(rows) == 1
    assert rows[0].asset_id == assets[0].id

    events = (await db_session.execute(
        select(Event).where(Event.listing_id == listing.id)
    )).scalars().all()
    by_type = {e.event_type: e.payload for e in events}
    assert "photo_analysis.completed" not in by_type
    assert "photo_compliance.completed" not in by_type


@pytest.mark.asyncio
async def test_no_ingested_assets_is_a_no_op(db_session, listing, assets):
    agent = PhotoAnalysisAgent(
        claude=MockClaudeClient(), session_factory=make_session_factory(db_session)
    )
    result = await agent.execute(
        AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    )
    assert result == {"analyzed": 0, "failed": 0, "flagged": 0}
    assert (await db_session.execute(select(VisionResult))).scalars().all() == []


@pytest.mark.asyncio
async def test_prefers_the_proxy_image_when_present(db_session, listing, assets):
    await _ingested(db_session, assets)
    assets[0].proxy_path = "proxies/hero.jpg"
    await db_session.flush()

    client = _client_for(assets, _three_analyses())
    seen: list[str] = []
    inner = client.analyze_images

    async def spy(image_urls, prompt, schema, **kw):
        seen.append(image_urls[0])
        return await inner(image_urls, prompt, schema, **kw)

    client.analyze_images = spy

    agent = PhotoAnalysisAgent(claude=client, session_factory=make_session_factory(db_session))
    await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id)))

    assert "https://mock/proxies/hero.jpg" in seen


@pytest.mark.asyncio
async def test_requests_a_short_lived_presigned_url(db_session, listing, assets, patch_storage):
    """Vision analysis URLs should be short-lived (300s), not the storage
    default, since they're only ever used for one immediate provider call."""
    await _ingested(db_session, assets)
    agent = PhotoAnalysisAgent(
        claude=_client_for(assets, _three_analyses()),
        session_factory=make_session_factory(db_session),
    )
    await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id)))

    for call in patch_storage.presigned_url.call_args_list:
        assert call.kwargs.get("expires_in") == 300
