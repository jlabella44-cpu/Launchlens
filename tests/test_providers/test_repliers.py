"""Tests for the Repliers provider (HTTP client + normalizer)."""
import pytest
from pytest_httpx import HTTPXMock

from listingjet.providers.repliers import RepliersClient, normalize_listing

BASE_URL = "https://api.repliers.io"


def _sample_listing(**overrides) -> dict:
    """A realistic Repliers listing record, overridable per-test."""
    base = {
        "mlsNumber": "C1234567",
        "listPrice": 850_000,
        "soldPrice": 835_000,
        "soldDate": "2024-11-04",
        "status": "Sld",
        "address": {
            "streetNumber": "123",
            "streetName": "Oak",
            "streetSuffix": "Ave",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
        },
        "details": {
            "numBedrooms": 3,
            "numBathrooms": 2,
            "sqft": 1800,
            "yearBuilt": 2010,
            "propertyType": "Residential",
        },
    }
    base.update(overrides)
    return base


# ----------------------------------------------------------------------
# RepliersClient — configuration guardrails
# ----------------------------------------------------------------------

def test_client_not_configured_when_no_key():
    client = RepliersClient(api_key="", base_url=BASE_URL)
    assert client.configured is False


def test_client_configured_with_key():
    client = RepliersClient(api_key="test-key", base_url=BASE_URL)
    assert client.configured is True


@pytest.mark.asyncio
async def test_search_listings_returns_empty_when_no_key():
    """Unconfigured client never makes an HTTP request."""
    client = RepliersClient(api_key="", base_url=BASE_URL)
    # pytest-httpx with no add_response would raise on any real request
    result = await client.search_listings({"city": "Austin"})
    assert result == []


@pytest.mark.asyncio
async def test_get_similar_returns_empty_when_no_key():
    client = RepliersClient(api_key="", base_url=BASE_URL)
    result = await client.get_similar("C1234567")
    assert result == []


# ----------------------------------------------------------------------
# RepliersClient — HTTP happy paths
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_listings_returns_listings_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/listings?city=Austin&pageSize=10",
        json={"listings": [_sample_listing(), _sample_listing(mlsNumber="C7654321")]},
    )
    client = RepliersClient(api_key="test-key", base_url=BASE_URL)
    result = await client.search_listings({"city": "Austin", "pageSize": 10})
    assert len(result) == 2
    assert result[0]["mlsNumber"] == "C1234567"


@pytest.mark.asyncio
async def test_search_listings_sends_api_key_header(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"listings": []})
    client = RepliersClient(api_key="secret-key-123", base_url=BASE_URL)
    await client.search_listings({"city": "Austin"})
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers.get("REPLIERS-API-KEY") == "secret-key-123"


@pytest.mark.asyncio
async def test_search_listings_handles_missing_listings_key(httpx_mock: HTTPXMock):
    """Server returns 200 with unexpected shape — we return empty list, not crash."""
    httpx_mock.add_response(json={"unexpected": "shape"})
    client = RepliersClient(api_key="test-key", base_url=BASE_URL)
    result = await client.search_listings({"city": "Austin"})
    assert result == []


@pytest.mark.asyncio
async def test_search_listings_swallows_http_error(httpx_mock: HTTPXMock):
    """A 500 from Repliers should not blow up the caller — return empty list."""
    httpx_mock.add_response(status_code=500, text="server error")
    client = RepliersClient(api_key="test-key", base_url=BASE_URL)
    result = await client.search_listings({"city": "Austin"})
    assert result == []


@pytest.mark.asyncio
async def test_get_similar_hits_correct_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{BASE_URL}/listings/C1234567/similar?pageSize=5",
        json={"listings": [_sample_listing()]},
    )
    client = RepliersClient(api_key="test-key", base_url=BASE_URL)
    result = await client.get_similar("C1234567", limit=5)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_similar_swallows_network_error(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(Exception("boom"))
    client = RepliersClient(api_key="test-key", base_url=BASE_URL)
    result = await client.get_similar("C1234567")
    assert result == []


# ----------------------------------------------------------------------
# normalize_listing — pure function, easy to exhaust
# ----------------------------------------------------------------------

def test_normalize_listing_happy_path():
    result = normalize_listing(_sample_listing())
    assert result == {
        "address": "123 Oak Ave, Austin",
        "beds": 3,
        "baths": 2.0,
        "sqft": 1800,
        "price": 835_000,  # soldPrice preferred over listPrice
        "price_per_sqft": 463.89,
        "sold_date": "2024-11-04",
        "mls_number": "C1234567",
    }


def test_normalize_listing_falls_back_to_list_price():
    """When soldPrice is missing, use listPrice."""
    raw = _sample_listing()
    raw.pop("soldPrice")
    result = normalize_listing(raw)
    assert result is not None
    assert result["price"] == 850_000


def test_normalize_listing_returns_none_when_no_price():
    raw = _sample_listing()
    raw.pop("soldPrice")
    raw.pop("listPrice")
    assert normalize_listing(raw) is None


def test_normalize_listing_returns_none_when_no_sqft():
    raw = _sample_listing()
    raw["details"] = {"numBedrooms": 3, "numBathrooms": 2}
    assert normalize_listing(raw) is None


def test_normalize_listing_handles_zero_sqft():
    raw = _sample_listing()
    raw["details"]["sqft"] = 0
    assert normalize_listing(raw) is None


def test_normalize_listing_handles_missing_address_parts():
    raw = _sample_listing()
    raw["address"] = {"streetName": "Oak", "city": "Austin"}
    result = normalize_listing(raw)
    assert result is not None
    assert result["address"] == "Oak, Austin"


def test_normalize_listing_handles_nulls_in_address_parts():
    raw = _sample_listing()
    raw["address"] = {
        "streetNumber": None,
        "streetName": "Oak",
        "streetSuffix": None,
        "city": "Austin",
    }
    result = normalize_listing(raw)
    assert result is not None
    assert result["address"] == "Oak, Austin"
