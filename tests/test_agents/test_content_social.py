import json

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.content_social import (
    ContentSocial,
    ContentSocialAgent,
    FacebookCopy,
    Hook,
    InstagramCopy,
    _tone_to_config,
)
from listingjet.models.outbox import Outbox
from listingjet.models.social_content import SocialContent
from listingjet.models.vision_result import VisionResult
from listingjet.providers.mock import MockClaudeClient
from tests.test_agents.conftest import make_session_factory

STYLES = ["storyteller", "data_driven", "luxury_minimalist", "urgency", "lifestyle"]


def _hooks(text: str) -> list[Hook]:
    return [Hook(style=s, caption=f"{s}: {text}") for s in STYLES]


def _copy(mls="Three-bedroom home with a renovated kitchen.", marketing="Sunlit rooms and a chef's kitchen."):
    return ContentSocial(
        mls_safe=mls,
        marketing=marketing,
        instagram=InstagramCopy(hooks=_hooks(marketing), hashtags=["#justlisted"] * 20, cta="Link in bio"),
        facebook=FacebookCopy(hooks=_hooks(marketing), cta="Book a showing"),
        tiktok_caption="Tour this one before it's gone.",
    )


async def _add_vr(db_session, asset_id, room_label="kitchen", hero_score=80, features=None):
    vr = VisionResult(
        asset_id=asset_id, tier=1, room_label=room_label, is_interior=True,
        quality_score=hero_score, commercial_score=hero_score, hero_score=hero_score,
        hero_candidate=hero_score >= 70, is_photo=True,
        features=features or ["quartz counters", "island"], raw_labels={}, model_used="claude-haiku-4-5",
    )
    db_session.add(vr)
    await db_session.flush()


def _agent(db_session, mock):
    return ContentSocialAgent(claude=mock, session_factory=make_session_factory(db_session))


@pytest.mark.asyncio
async def test_one_call_returns_copy_and_writes_three_social_rows(db_session, listing, assets):
    for a in assets:
        await _add_vr(db_session, a.id)
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy()]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    result = await _agent(db_session, mock).execute(ctx)

    assert result["mls_safe"].startswith("Three-bedroom")
    assert result["marketing"]
    assert result["fha_passed"] is True
    assert result["platforms"] == ["instagram", "facebook", "tiktok"]
    rows = (await db_session.execute(
        select(SocialContent).where(SocialContent.listing_id == listing.id).order_by(SocialContent.platform)
    )).scalars().all()
    by_platform = {r.platform: r for r in rows}
    assert set(by_platform) == {"facebook", "instagram", "tiktok"}
    ig_hooks = json.loads(by_platform["instagram"].caption)
    assert [h["style"] for h in ig_hooks] == STYLES
    assert len(by_platform["instagram"].hashtags) == 20
    assert by_platform["instagram"].cta == "Link in bio"
    assert by_platform["facebook"].hashtags is None
    assert by_platform["tiktok"].caption == "Tour this one before it's gone."


@pytest.mark.asyncio
async def test_call_uses_quality_model_and_8000_tokens(db_session, listing, assets, monkeypatch):
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy()]
    seen = {}
    orig = mock.complete_json

    async def spy(prompt, schema, **kw):
        seen.update(kw, prompt=prompt, schema=schema)
        return await orig(prompt, schema, **kw)

    monkeypatch.setattr(mock, "complete_json", spy)
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await _agent(db_session, mock).execute(ctx)

    assert seen["schema"] is ContentSocial
    assert seen["model"] == "claude-sonnet-5"
    assert seen["max_tokens"] == 8000
    assert seen["agent"] == "content_social"
    assert "temperature" not in seen
    assert seen["system"]  # tone system prompt present


@pytest.mark.asyncio
async def test_fha_violation_triggers_one_retry(db_session, listing, assets):
    bad = _copy(mls="Perfect for families in a safe neighborhood.")
    good = _copy()
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [bad, good]
    calls = []
    orig = mock.complete_json

    async def spy(prompt, schema, **kw):
        calls.append(prompt)
        return await orig(prompt, schema, **kw)

    mock.complete_json = spy
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await _agent(db_session, mock).execute(ctx)

    assert len(calls) == 2
    assert "Fair Housing Act" in calls[1]
    assert result["fha_passed"] is True
    assert result["mls_safe"] == good.mls_safe


@pytest.mark.asyncio
async def test_two_fha_failures_keep_first_and_flag(db_session, listing, assets):
    bad1 = _copy(mls="Great schools nearby.")
    bad2 = _copy(mls="Family friendly street.")
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [bad1, bad2]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await _agent(db_session, mock).execute(ctx)
    assert result["fha_passed"] is False
    assert result["mls_safe"] == bad1.mls_safe


@pytest.mark.asyncio
async def test_non_english_skips_fha(db_session, listing, assets):
    listing.metadata_ = {**(listing.metadata_ or {}), "language": "es"}
    await db_session.flush()
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy(mls="Perfecto para familias.")]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await _agent(db_session, mock).execute(ctx)
    assert result["language"] == "es"
    assert result["fha_passed"] is True


@pytest.mark.asyncio
async def test_rerun_replaces_social_rows(db_session, listing, assets):
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy(), _copy(marketing="Second pass.")]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    agent = _agent(db_session, mock)
    await agent.execute(ctx)
    await agent.execute(ctx)
    count = (await db_session.execute(
        select(SocialContent).where(SocialContent.listing_id == listing.id)
    )).scalars().all()
    assert len(count) == 3


@pytest.mark.asyncio
async def test_emits_completed_event(db_session, listing, assets):
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy()]
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await _agent(db_session, mock).execute(ctx)
    evt = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "content_social.completed")
    )).scalars().first()
    assert evt is not None
    assert evt.payload["platforms"] == ["instagram", "facebook", "tiktok"]


@pytest.mark.asyncio
async def test_prompt_contains_features_and_no_pii(db_session, listing, assets):
    listing.metadata_ = {**(listing.metadata_ or {}), "agent_email": "x@y.z", "owner_name": "Pat"}
    await db_session.flush()
    for a in assets:
        await _add_vr(db_session, a.id, features=["vaulted ceilings"])
    mock = MockClaudeClient()
    mock.responses[ContentSocial] = [_copy()]
    seen = {}
    orig = mock.complete_json

    async def spy(prompt, schema, **kw):
        seen["prompt"] = prompt
        return await orig(prompt, schema, **kw)

    mock.complete_json = spy
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await _agent(db_session, mock).execute(ctx)
    assert "vaulted ceilings" in seen["prompt"]
    assert "x@y.z" not in seen["prompt"] and "Pat" not in seen["prompt"]


def test_tone_to_config():
    assert _tone_to_config(0) == "utility"
    assert _tone_to_config(20) == "utility"
    assert _tone_to_config(50) == "balanced"
    assert _tone_to_config(90) == "high_flair"
