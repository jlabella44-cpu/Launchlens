from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.virtual_staging import VirtualStagingAgent
from listingjet.models.asset import Asset
from listingjet.models.event import Event
from listingjet.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory


def _fake_storage():
    storage = MagicMock()
    storage.presigned_url = MagicMock(
        side_effect=lambda key, **_kw: f"https://fake.example/{key}"
    )
    storage.upload = MagicMock()
    return storage


async def _add_vision_result(
    db_session, asset: Asset, *, room_label: str, is_empty_room: bool | None
) -> VisionResult:
    vr = VisionResult(
        asset_id=asset.id,
        tier=1,
        room_label=room_label,
        is_empty_room=is_empty_room,
        raw_labels={"room": room_label, "is_empty_room": is_empty_room},
    )
    db_session.add(vr)
    await db_session.flush()
    return vr


@pytest.fixture
async def fake_provider():
    provider = MagicMock()
    provider.stage_image = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n" + b"staged")
    return provider


@pytest.mark.asyncio
async def test_stages_only_empty_stageable_rooms(db_session, listing, assets, fake_provider):
    """Furnished rooms and non-stageable rooms are skipped; only an empty
    living room (is_empty_room=True) gets staged.
    """
    empty_living, furnished_bedroom, empty_bathroom = assets
    await _add_vision_result(
        db_session, empty_living, room_label="living_room", is_empty_room=True
    )
    await _add_vision_result(
        db_session, furnished_bedroom, room_label="bedroom", is_empty_room=False
    )
    await _add_vision_result(
        db_session, empty_bathroom, room_label="bathroom", is_empty_room=True
    )

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    agent = VirtualStagingAgent(
        staging_provider=fake_provider,
        storage_service=_fake_storage(),
        session_factory=make_session_factory(db_session),
    )

    result = await agent.execute(ctx)

    assert result["staged_count"] == 1
    fake_provider.stage_image.assert_awaited_once()
    call_kwargs = fake_provider.stage_image.await_args.kwargs
    assert call_kwargs["room_type"] == "living_room"

    staged_assets = (
        await db_session.execute(select(Asset).where(Asset.state == "staged"))
    ).scalars().all()
    assert len(staged_assets) == 1


@pytest.mark.asyncio
async def test_skips_with_no_provider_call_when_no_empty_rooms(
    db_session, listing, assets, fake_provider
):
    """Every candidate is either furnished or a non-stageable room type —
    the agent should skip before ever calling the provider.
    """
    furnished_living, furnished_bedroom, empty_bathroom = assets
    await _add_vision_result(
        db_session, furnished_living, room_label="living_room", is_empty_room=False
    )
    await _add_vision_result(
        db_session, furnished_bedroom, room_label="bedroom", is_empty_room=None
    )
    await _add_vision_result(
        db_session, empty_bathroom, room_label="bathroom", is_empty_room=True
    )

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    agent = VirtualStagingAgent(
        staging_provider=fake_provider,
        storage_service=_fake_storage(),
        session_factory=make_session_factory(db_session),
    )

    result = await agent.execute(ctx)

    assert result == {"skipped": True, "reason": "no_empty_rooms"}
    fake_provider.stage_image.assert_not_awaited()


@pytest.mark.asyncio
async def test_emits_completed_event(db_session, listing, assets, fake_provider):
    empty_living, *_rest = assets
    await _add_vision_result(
        db_session, empty_living, room_label="living_room", is_empty_room=True
    )

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    agent = VirtualStagingAgent(
        staging_provider=fake_provider,
        storage_service=_fake_storage(),
        session_factory=make_session_factory(db_session),
    )

    await agent.execute(ctx)

    events = (await db_session.execute(
        select(Event).where(Event.event_type == "virtual_staging.completed")
    )).scalars().all()
    assert len(events) == 1
    assert events[0].payload["staged_count"] == 1


@pytest.mark.asyncio
async def test_provider_failure_on_one_candidate_does_not_block_others(
    db_session, listing, assets
):
    empty_living, empty_bedroom, empty_bathroom = assets
    await _add_vision_result(
        db_session, empty_living, room_label="living_room", is_empty_room=True
    )
    await _add_vision_result(
        db_session, empty_bedroom, room_label="bedroom", is_empty_room=True
    )

    provider = MagicMock()
    provider.stage_image = AsyncMock(
        side_effect=[RuntimeError("provider blew up"), b"\x89PNG\r\n\x1a\n" + b"ok"]
    )

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    agent = VirtualStagingAgent(
        staging_provider=provider,
        storage_service=_fake_storage(),
        session_factory=make_session_factory(db_session),
    )

    result = await agent.execute(ctx)

    assert result["staged_count"] == 1
    assert provider.stage_image.await_count == 2


@pytest.mark.asyncio
async def test_storage_upload_failure_on_one_candidate_does_not_block_others(
    db_session, listing, assets, fake_provider
):
    """A storage.upload() failure for one asset should be caught like a
    provider failure: logged and skipped, while the other candidate still
    completes and the completion event still fires."""
    empty_living, empty_bedroom, empty_bathroom = assets
    await _add_vision_result(
        db_session, empty_living, room_label="living_room", is_empty_room=True
    )
    await _add_vision_result(
        db_session, empty_bedroom, room_label="bedroom", is_empty_room=True
    )

    storage = _fake_storage()
    storage.upload = MagicMock(side_effect=[RuntimeError("s3 blew up"), None])

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    agent = VirtualStagingAgent(
        staging_provider=fake_provider,
        storage_service=storage,
        session_factory=make_session_factory(db_session),
    )

    result = await agent.execute(ctx)

    assert result["staged_count"] == 1
    assert fake_provider.stage_image.await_count == 2
    assert storage.upload.call_count == 2

    staged_assets = (
        await db_session.execute(select(Asset).where(Asset.state == "staged"))
    ).scalars().all()
    assert len(staged_assets) == 1

    events = (await db_session.execute(
        select(Event).where(Event.event_type == "virtual_staging.completed")
    )).scalars().all()
    assert len(events) == 1
    assert events[0].payload["staged_count"] == 1
