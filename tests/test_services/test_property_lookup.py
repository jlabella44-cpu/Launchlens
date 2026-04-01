"""Tests for PropertyLookupService."""

from unittest.mock import AsyncMock, patch

import pytest

from listingjet.api.schemas.properties import PropertyLookupResponse
from listingjet.services.property_lookup import PropertyLookupService


@pytest.fixture
def svc():
    return PropertyLookupService()


ATTOM_RESPONSE_3BD = {
    "property": [
        {
            "building": {
                "rooms": {"beds": 3, "bathsfull": 2, "bathshalf": 1},
                "size": {"livingsize": 1850},
                "summary": {"yearbuilt": 1995, "proptype": "SFR"},
            },
            "lot": {"lotsize2": 7200},
        }
    ]
}

WALKSCORE_RESPONSE = {
    "walkscore": 72,
    "transit": {"score": 45},
    "bike": {"score": 58},
}


@pytest.mark.asyncio
async def test_lookup_returns_core_fields(svc: PropertyLookupService):
    with (
        patch.object(svc, "_call_attom", new_callable=AsyncMock, return_value=ATTOM_RESPONSE_3BD),
        patch.object(svc, "_call_walkscore", new_callable=AsyncMock, return_value={}),
    ):
        result = await svc.lookup("123 Main St, Springfield, IL 62704")

    assert isinstance(result, PropertyLookupResponse)
    assert result.found is True
    assert result.core.beds == 3
    assert result.core.baths == 2
    assert result.core.half_baths == 1
    assert result.core.sqft == 1850
    assert result.core.lot_sqft == 7200
    assert result.core.year_built == 1995
    assert result.details.property_type == "single_family"


@pytest.mark.asyncio
async def test_lookup_returns_neighborhood(svc: PropertyLookupService):
    with (
        patch.object(svc, "_call_attom", new_callable=AsyncMock, return_value=ATTOM_RESPONSE_3BD),
        patch.object(svc, "_call_walkscore", new_callable=AsyncMock, return_value=WALKSCORE_RESPONSE),
    ):
        result = await svc.lookup("123 Main St, Springfield, IL 62704")

    assert result.neighborhood.walk_score == 72
    assert result.neighborhood.transit_score == 45
    assert result.neighborhood.bike_score == 58


@pytest.mark.asyncio
async def test_lookup_not_found_returns_empty(svc: PropertyLookupService):
    with (
        patch.object(svc, "_call_attom", new_callable=AsyncMock, return_value={"property": []}),
        patch.object(svc, "_call_walkscore", new_callable=AsyncMock, return_value={}),
        patch("listingjet.services.property_lookup.generate_alternates", return_value=[]),
    ):
        result = await svc.lookup("999 Nowhere Blvd, Faketown, ZZ 00000")

    assert result.found is False
    assert result.core.beds is None


@pytest.mark.asyncio
async def test_lookup_retries_with_alternate_suffix(svc: PropertyLookupService):
    """First ATTOM call returns empty, second succeeds with alternate address."""
    empty = {"property": []}
    call_attom_mock = AsyncMock(side_effect=[empty, ATTOM_RESPONSE_3BD])

    with (
        patch.object(svc, "_call_attom", call_attom_mock),
        patch.object(svc, "_call_walkscore", new_callable=AsyncMock, return_value={}),
        patch(
            "listingjet.services.property_lookup.generate_alternates",
            return_value=["123 main street, springfield, il 62704"],
        ),
    ):
        result = await svc.lookup("123 Main St, Springfield, IL 62704")

    assert result.found is True
    assert result.core.beds == 3
    assert call_attom_mock.call_count == 2


@pytest.mark.asyncio
async def test_lookup_uses_cache(svc: PropertyLookupService):
    call_attom_mock = AsyncMock(return_value=ATTOM_RESPONSE_3BD)
    call_walkscore_mock = AsyncMock(return_value=WALKSCORE_RESPONSE)

    with (
        patch.object(svc, "_call_attom", call_attom_mock),
        patch.object(svc, "_call_walkscore", call_walkscore_mock),
    ):
        result1 = await svc.lookup("123 Main St, Springfield, IL 62704")
        result2 = await svc.lookup("123 Main St, Springfield, IL 62704")

    assert result1.core.beds == result2.core.beds
    assert call_attom_mock.call_count == 1
    assert call_walkscore_mock.call_count == 1
