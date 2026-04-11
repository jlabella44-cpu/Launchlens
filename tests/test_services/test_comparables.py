"""Tests for ComparablesService — Repliers-first with synthetic fallback."""
from unittest.mock import AsyncMock, patch

import pytest

from listingjet.providers.repliers import RepliersClient
from listingjet.services.comparables import (
    TARGET_COMP_COUNT,
    ComparablesService,
    _build_filters,
    _extract_city,
    _extract_state,
)


def _subject(**overrides) -> dict:
    base = {
        "address": "123 Main St, Austin, TX",
        "beds": 3,
        "baths": 2,
        "sqft": 1800,
        "year_built": 2010,
        "property_type": "single_family",
        "price": 450_000,
    }
    base.update(overrides)
    return base


def _raw_repliers_listing(price=425_000, sqft=1750, mls="C1234567") -> dict:
    return {
        "mlsNumber": mls,
        "soldPrice": price,
        "soldDate": "2024-11-04",
        "status": "Sld",
        "address": {
            "streetNumber": "456",
            "streetName": "Pine",
            "streetSuffix": "St",
            "city": "Austin",
            "state": "TX",
        },
        "details": {
            "numBedrooms": 3,
            "numBathrooms": 2,
            "sqft": sqft,
        },
    }


# ----------------------------------------------------------------------
# Pure helpers
# ----------------------------------------------------------------------

def test_extract_city_from_comma_string():
    assert _extract_city({"address": "123 Main St, Austin, TX"}) == "Austin"


def test_extract_city_from_dict():
    assert _extract_city({"address": {"city": "Austin", "state": "TX"}}) == "Austin"


def test_extract_city_empty_for_unparseable():
    assert _extract_city({"address": "not an address"}) == ""
    assert _extract_city({}) == ""


def test_extract_state_from_comma_string():
    assert _extract_state({"address": "123 Main St, Austin, TX"}) == "TX"


def test_extract_state_from_comma_string_with_zip():
    assert _extract_state({"address": "123 Main St, Austin, TX 78701"}) == "TX"


def test_build_filters_full_subject():
    filters = _build_filters(_subject())
    assert filters is not None
    assert filters["status"] == "Sld"
    assert filters["city"] == "Austin"
    assert filters["state"] == "TX"
    assert filters["minBedrooms"] == 2
    assert filters["maxBedrooms"] == 4
    assert 1400 <= filters["minSqft"] <= 1500  # ~20% under 1800
    assert 2100 <= filters["maxSqft"] <= 2200  # ~20% over 1800


def test_build_filters_returns_none_without_city():
    assert _build_filters({"beds": 3, "sqft": 1800}) is None


def test_build_filters_handles_missing_optional_fields():
    filters = _build_filters({"address": "X, Austin, TX"})
    assert filters is not None
    assert filters["city"] == "Austin"
    assert "minBedrooms" not in filters
    assert "minSqft" not in filters


# ----------------------------------------------------------------------
# ComparablesService.fetch() — feature-flag paths
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_uses_synthetic_when_flag_off():
    """repliers_cma_enabled=False → never calls Repliers, returns synthetic."""
    mock_client = RepliersClient(api_key="key", base_url="https://fake")
    mock_client.search_listings = AsyncMock(return_value=[])
    service = ComparablesService(repliers_client=mock_client)

    with patch("listingjet.services.comparables.settings.repliers_cma_enabled", False):
        result = await service.fetch(_subject())

    assert len(result) == TARGET_COMP_COUNT
    mock_client.search_listings.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_uses_synthetic_when_key_missing():
    """repliers_cma_enabled=True but no key → synthetic fallback."""
    mock_client = RepliersClient(api_key="", base_url="https://fake")
    mock_client.search_listings = AsyncMock(return_value=[])
    service = ComparablesService(repliers_client=mock_client)

    with patch("listingjet.services.comparables.settings.repliers_cma_enabled", True):
        result = await service.fetch(_subject())

    assert len(result) == TARGET_COMP_COUNT
    mock_client.search_listings.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_returns_repliers_comps_when_enabled_and_configured():
    mock_client = RepliersClient(api_key="key", base_url="https://fake")
    mock_client.search_listings = AsyncMock(return_value=[
        _raw_repliers_listing(price=425_000, sqft=1750, mls="A1"),
        _raw_repliers_listing(price=440_000, sqft=1850, mls="A2"),
        _raw_repliers_listing(price=410_000, sqft=1700, mls="A3"),
    ])
    service = ComparablesService(repliers_client=mock_client)

    with patch("listingjet.services.comparables.settings.repliers_cma_enabled", True):
        result = await service.fetch(_subject())

    assert len(result) == 3
    assert result[0]["mls_number"] == "A1"
    assert result[0]["price"] == 425_000
    assert result[0]["sqft"] == 1750
    mock_client.search_listings.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_falls_back_to_synthetic_on_empty_repliers():
    """Repliers returns [] → we fall back rather than return an empty CMA."""
    mock_client = RepliersClient(api_key="key", base_url="https://fake")
    mock_client.search_listings = AsyncMock(return_value=[])
    service = ComparablesService(repliers_client=mock_client)

    with patch("listingjet.services.comparables.settings.repliers_cma_enabled", True):
        result = await service.fetch(_subject())

    assert len(result) == TARGET_COMP_COUNT
    mock_client.search_listings.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_falls_back_to_synthetic_on_repliers_exception():
    """Repliers raises → fallback, no exception bubbles up."""
    mock_client = RepliersClient(api_key="key", base_url="https://fake")
    mock_client.search_listings = AsyncMock(side_effect=RuntimeError("boom"))
    service = ComparablesService(repliers_client=mock_client)

    with patch("listingjet.services.comparables.settings.repliers_cma_enabled", True):
        result = await service.fetch(_subject())

    assert len(result) == TARGET_COMP_COUNT


@pytest.mark.asyncio
async def test_fetch_caps_repliers_results_at_target_count():
    """Even if Repliers returns 20 results, we only keep TARGET_COMP_COUNT."""
    mock_client = RepliersClient(api_key="key", base_url="https://fake")
    mock_client.search_listings = AsyncMock(return_value=[
        _raw_repliers_listing(mls=f"X{i}") for i in range(20)
    ])
    service = ComparablesService(repliers_client=mock_client)

    with patch("listingjet.services.comparables.settings.repliers_cma_enabled", True):
        result = await service.fetch(_subject())

    assert len(result) == TARGET_COMP_COUNT


@pytest.mark.asyncio
async def test_fetch_skips_unnormalizable_listings():
    """Listings missing essential fields are dropped during normalization."""
    mock_client = RepliersClient(api_key="key", base_url="https://fake")
    mock_client.search_listings = AsyncMock(return_value=[
        _raw_repliers_listing(mls="GOOD"),
        {"mlsNumber": "BAD", "address": {}},  # no price, no sqft
        _raw_repliers_listing(mls="GOOD2"),
    ])
    service = ComparablesService(repliers_client=mock_client)

    with patch("listingjet.services.comparables.settings.repliers_cma_enabled", True):
        result = await service.fetch(_subject())

    assert len(result) == 2
    assert {c["mls_number"] for c in result} == {"GOOD", "GOOD2"}


@pytest.mark.asyncio
async def test_fetch_skips_repliers_when_city_unknown():
    """No city in subject → skip Repliers entirely (can't build a useful query)."""
    mock_client = RepliersClient(api_key="key", base_url="https://fake")
    mock_client.search_listings = AsyncMock(return_value=[])
    service = ComparablesService(repliers_client=mock_client)

    subject = {"beds": 3, "sqft": 1800, "price": 400_000}  # no address

    with patch("listingjet.services.comparables.settings.repliers_cma_enabled", True):
        result = await service.fetch(subject)

    assert len(result) == TARGET_COMP_COUNT  # synthetic fallback
    mock_client.search_listings.assert_not_called()


# ----------------------------------------------------------------------
# Synthetic fallback shape (locks the contract with CMAReportAgent)
# ----------------------------------------------------------------------

def test_synthetic_comparables_shape():
    comps = ComparablesService._synthetic_comparables(_subject())
    assert len(comps) == TARGET_COMP_COUNT
    for c in comps:
        assert {"address", "beds", "baths", "sqft", "price", "price_per_sqft"} <= set(c)
        assert isinstance(c["price"], int)
        assert isinstance(c["sqft"], int)
        assert c["sqft"] > 0
        assert c["price"] > 0
