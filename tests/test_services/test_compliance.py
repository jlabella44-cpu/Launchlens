# tests/test_services/test_compliance.py
import uuid

import pytest

from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.vision_result import VisionResult
from listingjet.services.compliance import compliance_report

CLEAN = {"people": False, "signage": False, "branding": False, "text_overlay": False}
FLAGGED = {"people": False, "signage": False, "branding": False, "text_overlay": True}


@pytest.fixture
async def listing(db_session):
    obj = Listing(
        tenant_id=uuid.uuid4(),
        address={"street": "9 Compliance Way", "city": "Austin", "state": "TX"},
        metadata_={},
        state=ListingState.AWAITING_REVIEW,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


async def _asset(db_session, listing, name: str, compliance: dict | None, tier: int = 1) -> Asset:
    a = Asset(
        listing_id=listing.id,
        tenant_id=listing.tenant_id,
        file_path=f"listings/{listing.id}/{name}.jpg",
        file_hash=name,
        state="ingested",
    )
    db_session.add(a)
    await db_session.flush()
    if compliance is not None:
        db_session.add(VisionResult(
            asset_id=a.id, tier=tier, room_label="living_room", is_photo=True,
            compliance=compliance, model_used="claude-haiku-4-5",
        ))
        await db_session.flush()
    return a


async def _package(db_session, listing, assets):
    for pos, a in enumerate(assets):
        db_session.add(PackageSelection(
            tenant_id=listing.tenant_id, listing_id=listing.id, asset_id=a.id,
            channel="mls", position=pos, selected_by="ai",
        ))
    await db_session.flush()


@pytest.mark.asyncio
async def test_report_flags_the_text_overlay_photo(db_session, listing):
    clean = await _asset(db_session, listing, "clean", CLEAN)
    bad = await _asset(db_session, listing, "bad", FLAGGED)
    await _package(db_session, listing, [clean, bad])

    report = await compliance_report(db_session, listing.id)

    assert report["total_photos"] == 2
    assert report["compliant_count"] == 1
    assert report["flagged_count"] == 1
    assert report["all_compliant"] is False

    decisions = {d["asset_id"]: d for d in report["decisions"]}
    assert decisions[str(clean.id)]["compliant"] is True
    assert decisions[str(clean.id)]["reasoning"] == "No issues found"
    assert decisions[str(bad.id)]["compliant"] is False
    assert decisions[str(bad.id)]["text_overlay"] is True
    assert "text overlay" in decisions[str(bad.id)]["reasoning"]

    flagged = report["flagged_photos"]
    assert len(flagged) == 1
    assert flagged[0]["asset_id"] == str(bad.id)
    assert flagged[0]["text_overlay"] is True
    assert "text overlay" in flagged[0]["issues_summary"]


@pytest.mark.asyncio
async def test_all_compliant_when_nothing_flagged(db_session, listing):
    a = await _asset(db_session, listing, "a", CLEAN)
    b = await _asset(db_session, listing, "b", CLEAN)
    await _package(db_session, listing, [a, b])

    report = await compliance_report(db_session, listing.id)
    assert report["all_compliant"] is True
    assert report["flagged_count"] == 0
    assert report["flagged_photos"] == []


@pytest.mark.asyncio
async def test_falls_back_to_all_analysed_assets_when_nothing_packaged(db_session, listing):
    await _asset(db_session, listing, "a", CLEAN)
    await _asset(db_session, listing, "b", FLAGGED)

    report = await compliance_report(db_session, listing.id)
    assert report["total_photos"] == 2
    assert report["flagged_count"] == 1


@pytest.mark.asyncio
async def test_assets_without_analysis_are_excluded(db_session, listing):
    analysed = await _asset(db_session, listing, "analysed", CLEAN)
    await _asset(db_session, listing, "unanalysed", None)

    report = await compliance_report(db_session, listing.id)
    assert report["total_photos"] == 1
    assert report["decisions"][0]["asset_id"] == str(analysed.id)


@pytest.mark.asyncio
async def test_empty_listing_returns_a_compliant_empty_report(db_session, listing):
    report = await compliance_report(db_session, listing.id)
    assert report == {
        "total_photos": 0,
        "compliant_count": 0,
        "flagged_count": 0,
        "all_compliant": True,
        "decisions": [],
        "flagged_photos": [],
    }
