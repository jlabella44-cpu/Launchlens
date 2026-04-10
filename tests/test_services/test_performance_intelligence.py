"""Tests for Performance Intelligence service."""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from listingjet.services.performance_intelligence import (
    compute_tenant_insights,
    get_listing_insight,
)


def _mock_outcome(**kwargs):
    defaults = {
        "listing_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "days_on_market": 25,
        "final_price": 400000,
        "original_price": 420000,
        "price_change_count": 1,
        "status": "sold",
        "avg_photo_quality": 82.0,
        "avg_commercial_score": 70.0,
        "hero_quality": 90.0,
        "coverage_pct": 100.0,
        "photo_count": 25,
        "room_diversity": 6,
        "override_rate": 0.05,
        "health_score_at_delivery": 85,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_compute_insights_insufficient_data():
    """Less than MIN_SAMPLE_SIZE listings → no insights."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [_mock_outcome() for _ in range(3)]
    session.execute = AsyncMock(return_value=result_mock)
    session.flush = AsyncMock()

    insights = await compute_tenant_insights(session, uuid.uuid4())
    assert insights == []


@pytest.mark.asyncio
async def test_compute_insights_with_sufficient_data():
    """Enough listings → generates DOM summary + correlation insights."""
    outcomes = [
        _mock_outcome(avg_photo_quality=90, days_on_market=15),
        _mock_outcome(avg_photo_quality=85, days_on_market=18),
        _mock_outcome(avg_photo_quality=80, days_on_market=20),
        _mock_outcome(avg_photo_quality=60, days_on_market=35),
        _mock_outcome(avg_photo_quality=55, days_on_market=40),
        _mock_outcome(avg_photo_quality=50, days_on_market=45),
    ]

    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = outcomes
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.flush = AsyncMock()

    insights = await compute_tenant_insights(session, uuid.uuid4())
    types = [i["type"] for i in insights]

    assert "dom_summary" in types
    assert "quality_dom_correlation" in types

    # Quality correlation should show high-quality listings sell faster
    quality_insight = next(i for i in insights if i["type"] == "quality_dom_correlation")
    assert quality_insight["data"]["high_quality_avg_dom"] < quality_insight["data"]["low_quality_avg_dom"]


@pytest.mark.asyncio
async def test_get_listing_insight_not_found():
    """No outcome data → returns None."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    result = await get_listing_insight(session, uuid.uuid4(), uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_listing_insight_with_data():
    """Listing with outcome → returns comparisons."""
    listing_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    outcome = _mock_outcome(
        listing_id=listing_id,
        tenant_id=tenant_id,
        days_on_market=20,
        avg_photo_quality=88.0,
    )

    avg_row = SimpleNamespace(avg_dom=28.0, avg_quality=75.0, total=10)

    session = AsyncMock()
    # First call: get outcome, second call: get averages
    outcome_result = MagicMock()
    outcome_result.scalar_one_or_none.return_value = outcome
    avg_result = MagicMock()
    avg_result.one.return_value = avg_row

    session.execute = AsyncMock(side_effect=[outcome_result, avg_result])

    result = await get_listing_insight(session, listing_id, tenant_id)
    assert result is not None
    assert result["listing_id"] == str(listing_id)
    assert result["comparisons"]["dom_vs_avg"]["better"] is True
    assert result["comparisons"]["quality_vs_avg"]["better"] is True
