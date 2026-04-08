"""Tests for the OutcomeTracker service — Phase 5 Performance Intelligence."""
import uuid

import pytest
from sqlalchemy import select

from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.listing_outcome import ListingOutcome
from listingjet.models.package_selection import PackageSelection
from listingjet.models.performance_event import PerformanceEvent
from listingjet.models.photo_outcome_correlation import PhotoOutcomeCorrelation
from listingjet.models.vision_result import VisionResult
from listingjet.services.outcome_tracker import (
    _compute_grade,
    _position_bucket,
    _quality_bucket,
    compute_correlations,
    get_insights,
    get_outcome_boost,
    ingest_outcome,
)


@pytest.fixture
async def tenant_id():
    return uuid.uuid4()


@pytest.fixture
async def delivered_listing(db_session, tenant_id):
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "100 Oak Ave", "city": "Denver", "state": "CO"},
        metadata_={"beds": 3, "baths": 2, "sqft": 2000, "price": 450000},
        state=ListingState.DELIVERED,
    )
    db_session.add(listing)
    await db_session.flush()
    return listing


@pytest.fixture
async def listing_with_package(db_session, delivered_listing, tenant_id):
    """Create a delivered listing with assets, vision results, and package selections."""
    assets = []
    for i, room in enumerate(["exterior", "kitchen", "living_room"]):
        asset = Asset(
            listing_id=delivered_listing.id,
            tenant_id=tenant_id,
            file_path=f"s3://bucket/{delivered_listing.id}/photo_{i}.jpg",
            file_hash=f"hash{i:03d}",
            state="uploaded",
        )
        db_session.add(asset)
        assets.append(asset)
    await db_session.flush()

    for i, (asset, room) in enumerate(zip(assets, ["exterior", "kitchen", "living_room"])):
        vr = VisionResult(
            asset_id=asset.id,
            tier=1,
            room_label=room,
            quality_score=70 + i * 5,
            commercial_score=60 + i * 5,
            hero_candidate=(i == 0),
        )
        db_session.add(vr)

        ps = PackageSelection(
            tenant_id=tenant_id,
            listing_id=delivered_listing.id,
            asset_id=asset.id,
            channel="mls",
            position=i,
            selected_by="ai",
            composite_score=0.7 + i * 0.05,
        )
        db_session.add(ps)

    await db_session.flush()
    return delivered_listing, assets


# ---- Unit tests for helper functions ----


def test_compute_grade_fast_sale():
    assert _compute_grade(10, 1.02) == "A"


def test_compute_grade_slow_sale():
    assert _compute_grade(100, 0.85) == "F"


def test_compute_grade_average():
    assert _compute_grade(25, 0.98) == "B"


def test_compute_grade_none_values():
    assert _compute_grade(None, None) == "C"


def test_quality_bucket_high():
    assert _quality_bucket(85) == "high"


def test_quality_bucket_medium():
    assert _quality_bucket(60) == "medium"


def test_quality_bucket_low():
    assert _quality_bucket(30) == "low"


def test_quality_bucket_none():
    assert _quality_bucket(None) == "unknown"


def test_position_bucket_hero():
    assert _position_bucket(0) == "hero"


def test_position_bucket_top5():
    assert _position_bucket(3) == "top_5"


def test_position_bucket_mid():
    assert _position_bucket(10) == "mid"


def test_position_bucket_tail():
    assert _position_bucket(20) == "tail"


# ---- Integration tests for ingest_outcome ----


@pytest.mark.asyncio
async def test_ingest_outcome_creates_record(db_session, listing_with_package, tenant_id):
    listing, assets = listing_with_package

    idx_data = {
        "StandardStatus": "Closed",
        "ListPrice": 450000,
        "ClosePrice": 460000,
        "DaysOnMarket": 12,
    }

    outcome = await ingest_outcome(db_session, listing.id, tenant_id, idx_data, source="test_feed")

    assert outcome.status == "closed"
    assert outcome.list_price == 450000.0
    assert outcome.sale_price == 460000.0
    assert outcome.price_ratio == pytest.approx(460000 / 450000, abs=0.001)
    assert outcome.days_on_market == 12
    assert outcome.outcome_grade == "A"
    assert outcome.total_photos_mls == 3
    assert outcome.hero_room_label == "exterior"
    assert outcome.avg_photo_score is not None


@pytest.mark.asyncio
async def test_ingest_outcome_updates_on_second_call(db_session, listing_with_package, tenant_id):
    listing, _ = listing_with_package

    # First: active
    await ingest_outcome(db_session, listing.id, tenant_id, {"StandardStatus": "Active"})
    # Second: closed
    outcome = await ingest_outcome(
        db_session, listing.id, tenant_id,
        {"StandardStatus": "Closed", "ListPrice": 400000, "ClosePrice": 395000, "DaysOnMarket": 45},
    )

    assert outcome.status == "closed"
    assert outcome.days_on_market == 45

    # Should only have one record (upsert)
    result = await db_session.execute(
        select(ListingOutcome).where(ListingOutcome.listing_id == listing.id)
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_ingest_outcome_counts_price_changes(db_session, listing_with_package, tenant_id):
    listing, _ = listing_with_package

    # Add price change events
    for i in range(3):
        db_session.add(PerformanceEvent(
            tenant_id=tenant_id,
            listing_id=listing.id,
            signal_type="idx.price_change",
            value=400000 + i * 5000,
            source="test",
        ))
    await db_session.flush()

    outcome = await ingest_outcome(
        db_session, listing.id, tenant_id,
        {"StandardStatus": "Closed", "DaysOnMarket": 60},
    )
    assert outcome.price_changes == 3


# ---- Integration tests for compute_correlations ----


@pytest.mark.asyncio
async def test_compute_correlations_skips_below_min(db_session, tenant_id):
    """With fewer than 3 closed listings, correlations are skipped."""
    count = await compute_correlations(db_session, tenant_id)
    assert count == 0


@pytest.mark.asyncio
async def test_compute_correlations_generates_data(db_session, tenant_id):
    """Create 3 closed listings with packages, then verify correlations are computed."""
    listings_data = []
    for i in range(3):
        listing = Listing(
            tenant_id=tenant_id,
            address={"street": f"{100 + i} Main St"},
            metadata_={},
            state=ListingState.DELIVERED,
        )
        db_session.add(listing)
        await db_session.flush()

        asset = Asset(
            listing_id=listing.id,
            tenant_id=tenant_id,
            file_path=f"s3://bucket/{listing.id}/photo.jpg",
            file_hash=f"hash_{i}",
            state="uploaded",
        )
        db_session.add(asset)
        await db_session.flush()

        vr = VisionResult(
            asset_id=asset.id, tier=1, room_label="exterior",
            quality_score=70 + i * 5, commercial_score=60, hero_candidate=True,
        )
        db_session.add(vr)

        ps = PackageSelection(
            tenant_id=tenant_id, listing_id=listing.id, asset_id=asset.id,
            channel="mls", position=0, composite_score=0.75,
        )
        db_session.add(ps)

        outcome = ListingOutcome(
            tenant_id=tenant_id, listing_id=listing.id, status="closed",
            list_price=400000, sale_price=410000, price_ratio=1.025,
            days_on_market=15 + i * 5, outcome_grade="A" if i < 2 else "B",
        )
        db_session.add(outcome)
        listings_data.append((listing, asset))

    await db_session.flush()

    count = await compute_correlations(db_session, tenant_id)
    assert count > 0

    # Check that room_label correlations were created
    result = await db_session.execute(
        select(PhotoOutcomeCorrelation).where(
            PhotoOutcomeCorrelation.tenant_id == tenant_id,
            PhotoOutcomeCorrelation.dimension == "room_label",
        )
    )
    room_corrs = result.scalars().all()
    assert len(room_corrs) >= 1
    assert room_corrs[0].sample_count == 3


# ---- Tests for get_outcome_boost ----


@pytest.mark.asyncio
async def test_get_outcome_boost_returns_default(db_session, tenant_id):
    """With no correlations, boost is 1.0."""
    boost = await get_outcome_boost(db_session, tenant_id, "exterior")
    assert boost == 1.0


@pytest.mark.asyncio
async def test_get_outcome_boost_returns_stored_value(db_session, tenant_id):
    db_session.add(PhotoOutcomeCorrelation(
        tenant_id=tenant_id, dimension="room_label", dimension_value="kitchen",
        sample_count=5, outcome_boost=1.15,
    ))
    await db_session.flush()

    boost = await get_outcome_boost(db_session, tenant_id, "kitchen")
    assert boost == pytest.approx(1.15)


# ---- Tests for get_insights ----


@pytest.mark.asyncio
async def test_get_insights_empty_tenant(db_session, tenant_id):
    result = await get_insights(db_session, tenant_id)
    assert result["outcomes_count"] == 0
    assert "No closed listings" in result["summary"]


@pytest.mark.asyncio
async def test_get_insights_with_data(db_session, tenant_id):
    # Create one closed outcome
    listing = Listing(
        tenant_id=tenant_id, address={"street": "1 Test St"},
        metadata_={}, state=ListingState.DELIVERED,
    )
    db_session.add(listing)
    await db_session.flush()

    db_session.add(ListingOutcome(
        tenant_id=tenant_id, listing_id=listing.id, status="closed",
        days_on_market=20, price_ratio=0.98, outcome_grade="B",
    ))
    await db_session.flush()

    result = await get_insights(db_session, tenant_id)
    assert result["outcomes_count"] == 1
    assert result["avg_dom"] == 20.0
    assert result["grade_distribution"]["B"] == 1
