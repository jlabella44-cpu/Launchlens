import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.photo_compliance import PhotoComplianceAgent
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from tests.test_agents.conftest import make_session_factory


async def _setup_listing_with_package(db_session, num_photos=3):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "100 Compliance Ave", "city": "Austin", "state": "TX"},
        metadata_={"beds": 3, "baths": 2},
        state=ListingState.AWAITING_REVIEW,
    )
    db_session.add(listing)
    await db_session.flush()

    assets = []
    for i in range(num_photos):
        asset = Asset(
            listing_id=listing.id,
            tenant_id=tenant_id,
            file_path=f"listings/{listing.id}/photos/photo_{i}.jpg",
            file_hash=f"hash{i:03d}",
            state="uploaded",
        )
        db_session.add(asset)
        assets.append(asset)
    await db_session.flush()

    for i, asset in enumerate(assets):
        pkg = PackageSelection(
            tenant_id=tenant_id,
            listing_id=listing.id,
            asset_id=asset.id,
            channel="mls",
            position=i,
            composite_score=90.0 - i,
            selected_by="ai",
        )
        db_session.add(pkg)
    await db_session.flush()

    return listing, tenant_id, assets


def _make_compliant_response():
    return json.dumps({
        "branding": {"detected": False, "details": ""},
        "signage": {"detected": False, "details": ""},
        "people": {"detected": False, "details": ""},
        "text_overlay": {"detected": False, "details": ""},
        "overall_compliant": True,
        "issues_summary": "No issues found",
    })


def _make_flagged_response():
    return json.dumps({
        "branding": {"detected": True, "details": "Brokerage watermark in bottom-right corner"},
        "signage": {"detected": True, "details": "For Sale sign visible in front yard"},
        "people": {"detected": False, "details": ""},
        "text_overlay": {"detected": False, "details": ""},
        "overall_compliant": False,
        "issues_summary": "Branding watermark and For Sale sign detected",
    })


def _make_vision_provider(responses):
    """Mock vision provider that returns canned responses in order."""
    provider = MagicMock()
    provider.analyze_with_prompt = AsyncMock(side_effect=responses)
    return provider


def _make_storage():
    storage = MagicMock()
    storage.presigned_url = MagicMock(return_value="https://s3.example.com/presigned")
    return storage


@pytest.mark.asyncio
async def test_all_photos_compliant(db_session):
    listing, tenant_id, assets = await _setup_listing_with_package(db_session, 3)
    responses = [_make_compliant_response()] * 3
    vision = _make_vision_provider(responses)
    storage = _make_storage()

    agent = PhotoComplianceAgent(
        vision_provider=vision,
        storage_service=storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    report = await agent.execute(ctx)

    assert report["total_photos"] == 3
    assert report["compliant_count"] == 3
    assert report["flagged_count"] == 0
    assert report["all_compliant"] is True
    assert len(report["flagged_photos"]) == 0


@pytest.mark.asyncio
async def test_flagged_photos_reported(db_session):
    listing, tenant_id, assets = await _setup_listing_with_package(db_session, 3)
    responses = [_make_compliant_response(), _make_flagged_response(), _make_compliant_response()]
    vision = _make_vision_provider(responses)
    storage = _make_storage()

    agent = PhotoComplianceAgent(
        vision_provider=vision,
        storage_service=storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    report = await agent.execute(ctx)

    assert report["total_photos"] == 3
    assert report["flagged_count"] == 1
    assert report["all_compliant"] is False
    flagged = report["flagged_photos"][0]
    assert flagged["branding"] is True
    assert flagged["signage"] is True
    assert flagged["people"] is False


@pytest.mark.asyncio
async def test_vision_failure_treated_as_compliant(db_session):
    listing, tenant_id, assets = await _setup_listing_with_package(db_session, 2)
    vision = MagicMock()
    vision.analyze_with_prompt = AsyncMock(side_effect=Exception("API down"))
    storage = _make_storage()

    agent = PhotoComplianceAgent(
        vision_provider=vision,
        storage_service=storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    report = await agent.execute(ctx)

    assert report["total_photos"] == 2
    assert report["all_compliant"] is True
    assert report["flagged_count"] == 0


@pytest.mark.asyncio
async def test_compliance_emits_event(db_session):
    from sqlalchemy import select

    from listingjet.models.outbox import Outbox

    listing, tenant_id, assets = await _setup_listing_with_package(db_session, 1)
    vision = _make_vision_provider([_make_compliant_response()])
    storage = _make_storage()

    agent = PhotoComplianceAgent(
        vision_provider=vision,
        storage_service=storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "photo_compliance.completed")
    )).scalars().all()
    assert len(rows) == 1
