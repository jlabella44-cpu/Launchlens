"""Unit tests for the health score service."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from listingjet.services.health_score import (
    DEFAULT_WEIGHTS,
    PLAN_SUBSCORES,
    _clamp,
    _resolve_weights,
    calculate_media_score,
    calculate_content_score,
    calculate_velocity_score,
    calculate_syndication_score,
    calculate_market_score,
)


# -- Weight resolution tests --

def test_resolve_weights_starter():
    w = _resolve_weights("starter")
    assert set(w.keys()) == {"media", "content"}
    assert abs(sum(w.values()) - 1.0) < 0.01


def test_resolve_weights_pro():
    w = _resolve_weights("pro")
    assert set(w.keys()) == {"media", "content", "velocity", "syndication"}
    assert abs(sum(w.values()) - 1.0) < 0.01


def test_resolve_weights_enterprise():
    w = _resolve_weights("enterprise")
    assert set(w.keys()) == {"media", "content", "velocity", "syndication", "market"}
    assert abs(sum(w.values()) - 1.0) < 0.01


def test_resolve_weights_custom_enterprise():
    custom = {"media": 0.5, "content": 0.1, "velocity": 0.1, "syndication": 0.2, "market": 0.1}
    w = _resolve_weights("enterprise", custom)
    assert w == custom


def test_resolve_weights_custom_ignored_for_non_enterprise():
    custom = {"media": 0.5, "content": 0.5}
    w = _resolve_weights("pro", custom)
    # Should use default pro weights, not custom
    assert "velocity" in w


def test_clamp():
    assert _clamp(150) == 100
    assert _clamp(-10) == 0
    assert _clamp(75.6) == 75


# -- Media score tests (sync logic tested via engagement_score equivalence) --

@pytest.mark.asyncio
async def test_calculate_media_score_no_results():
    """No vision results → default score of 50."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)

    score, details = await calculate_media_score(session, uuid.uuid4())
    assert score == 50
    assert details["avg_quality"] == 0


@pytest.mark.asyncio
async def test_calculate_media_score_with_results():
    """Good quality photos → high media score."""
    vr1 = SimpleNamespace(quality_score=90, commercial_score=80, hero_candidate=True, room_label="exterior")
    vr2 = SimpleNamespace(quality_score=85, commercial_score=70, hero_candidate=False, room_label="kitchen")
    vr3 = SimpleNamespace(quality_score=80, commercial_score=75, hero_candidate=False, room_label="bedroom")
    vr4 = SimpleNamespace(quality_score=88, commercial_score=72, hero_candidate=False, room_label="bathroom")
    vr5 = SimpleNamespace(quality_score=82, commercial_score=68, hero_candidate=False, room_label="living_room")

    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [vr1, vr2, vr3, vr4, vr5]
    session.execute = AsyncMock(return_value=result_mock)

    score, details = await calculate_media_score(session, uuid.uuid4())
    assert score > 70  # Good photos should yield good score
    assert details["coverage_pct"] == 100.0  # All 5 required shots present
    assert details["hero_strength"] == 80  # Hero's commercial score


# -- Content score tests --

@pytest.mark.asyncio
async def test_calculate_content_score_full():
    """Fully content-ready listing → 100."""
    listing_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    listing = SimpleNamespace(
        state=SimpleNamespace(value="delivered"),
        mls_bundle_path="s3://bundles/mls.zip",
        marketing_bundle_path="s3://bundles/marketing.zip",
    )
    brand_kit = SimpleNamespace(logo_url="https://logo.png", primary_color="#2563EB")

    session = AsyncMock()
    session.get = AsyncMock(side_effect=lambda cls, id: listing if id == listing_id else brand_kit if id == tenant_id else None)

    # Social content count = 3, FHA violations = 0
    social_result = MagicMock()
    social_result.scalar.return_value = 3
    fha_result = MagicMock()
    fha_result.scalar.return_value = 0
    brand_result = MagicMock()
    brand_result.scalar_one_or_none.return_value = brand_kit

    call_count = 0
    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return social_result  # social count
        elif call_count == 2:
            return fha_result     # fha count
        return brand_result       # brand kit

    session.execute = mock_execute

    score, details = await calculate_content_score(session, listing_id, tenant_id)
    assert score == 100
    assert details["description"] is True
    assert details["fha_passed"] is True
    assert details["social"] is True
    assert details["export"] is True


@pytest.mark.asyncio
async def test_calculate_content_score_minimal():
    """Listing with no content outputs → 0."""
    listing_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    listing = SimpleNamespace(
        state=SimpleNamespace(value="uploading"),
        mls_bundle_path=None,
        marketing_bundle_path=None,
    )

    session = AsyncMock()
    session.get = AsyncMock(return_value=listing)

    # social count = 0, fha violations = 1
    social_result = MagicMock()
    social_result.scalar.return_value = 0
    fha_result = MagicMock()
    fha_result.scalar.return_value = 1
    brand_result = MagicMock()
    brand_result.scalar_one_or_none.return_value = None

    results = iter([social_result, fha_result, brand_result])
    session.execute = AsyncMock(side_effect=lambda stmt: next(results))

    score, details = await calculate_content_score(session, listing_id, tenant_id)
    assert score == 0
    assert details["description"] is False
    assert details["fha_passed"] is False


# -- Velocity score tests --

@pytest.mark.asyncio
async def test_calculate_velocity_score_fast_pipeline():
    """Fast pipeline with no issues → high score."""
    listing_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    now = datetime.now(timezone.utc)
    listing = SimpleNamespace(
        state=SimpleNamespace(value="delivered"),
        updated_at=now,
        created_at=now.replace(minute=now.minute - 5) if now.minute >= 5 else now,
    )

    session = AsyncMock()

    # No performance events
    events_result = MagicMock()
    events_result.scalars.return_value.all.return_value = []

    # Package selections count
    selections_result = MagicMock()
    selections_result.scalar.return_value = 25

    session.execute = AsyncMock(side_effect=[events_result, selections_result])
    session.get = AsyncMock(return_value=listing)

    score, details = await calculate_velocity_score(session, listing_id, tenant_id)
    assert score >= 80  # Fast pipeline should be healthy


# -- Syndication score tests --

@pytest.mark.asyncio
async def test_calculate_syndication_score_no_idx():
    """No IDX data → neutral 50."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)

    score, details = await calculate_syndication_score(session, uuid.uuid4())
    assert score == 50
    assert details["idx_active"] is None


@pytest.mark.asyncio
async def test_calculate_syndication_score_active_listing():
    """Active IDX listing with matching photos → high score."""
    status_event = SimpleNamespace(signal_type="idx.status_change", value=1.0, recorded_at=datetime.now(timezone.utc))
    dom_event = SimpleNamespace(signal_type="idx.dom_update", value=7.0, recorded_at=datetime.now(timezone.utc))
    photo_event = SimpleNamespace(signal_type="idx.photo_count", value=25.0, recorded_at=datetime.now(timezone.utc))

    session = AsyncMock()

    # IDX events result
    idx_result = MagicMock()
    idx_result.scalars.return_value.all.return_value = [status_event, dom_event, photo_event]

    # Package selections count for photo match
    selections_result = MagicMock()
    selections_result.scalar.return_value = 25

    session.execute = AsyncMock(side_effect=[idx_result, selections_result])

    score, details = await calculate_syndication_score(session, uuid.uuid4())
    assert score == 100  # Active + good DOM + exact photo match
    assert details["idx_active"] is True
    assert details["dom"] == 7


# -- Market score tests --

@pytest.mark.asyncio
async def test_calculate_market_score_no_data():
    """No market data → neutral 50."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)

    score, details = await calculate_market_score(session, uuid.uuid4())
    assert score == 50


@pytest.mark.asyncio
async def test_calculate_market_score_stable_listing():
    """Stable active listing with no price changes → high score."""
    status_event = SimpleNamespace(
        signal_type="idx.status_change", value=1.0, recorded_at=datetime.now(timezone.utc),
    )

    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [status_event]
    session.execute = AsyncMock(return_value=result_mock)

    score, details = await calculate_market_score(session, uuid.uuid4())
    assert score == 100
    assert details["price_changes"] == 0
    assert details["status"] == "active"
