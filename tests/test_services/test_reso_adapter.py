"""Tests for the RESO Web API adapter — OAuth2, Data Dictionary mapping,
property/media submission."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from listingjet.services.reso_adapter import (
    RESOAdapter,
    RESOConnectionConfig,
    _extract_street_name,
    _extract_street_number,
    build_media_payload,
    map_listing_to_reso,
)

BASE_URL = "https://reso.example.com/api"
TOKEN_URL = "https://reso.example.com/oauth2/token"


def _make_config(**overrides) -> RESOConnectionConfig:
    defaults = {
        "base_url": BASE_URL,
        "oauth_token_url": TOKEN_URL,
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
    }
    defaults.update(overrides)
    return RESOConnectionConfig(**defaults)


def _ok_response(json_data=None, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    return resp


def _error_response(status_code=500):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=resp))
    return resp


# --- Data Dictionary Mapping Tests ---


def test_map_listing_to_reso_basic():
    addr = {"street": "123 Main St", "city": "Austin", "state": "TX", "zip": "78701"}
    meta = {"beds": 3, "baths": 2.5, "sqft": 1800, "price": 500000, "property_type": "single_family"}

    result = map_listing_to_reso(addr, meta)

    assert result["PropertyType"] == "Residential"
    assert result["StreetNumber"] == "123"
    assert result["StreetName"] == "Main St"
    assert result["City"] == "Austin"
    assert result["StateOrProvince"] == "TX"
    assert result["PostalCode"] == "78701"
    assert result["ListPrice"] == 500000
    assert result["BedroomsTotal"] == 3
    assert result["BathroomsTotalInteger"] == 2
    assert result["BathroomsFull"] == 2
    assert result["BathroomsHalf"] == 1
    assert result["LivingArea"] == 1800


def test_map_listing_to_reso_minimal():
    addr = {"city": "Denver", "state": "CO"}
    meta = {}

    result = map_listing_to_reso(addr, meta)

    assert result["City"] == "Denver"
    assert result["StateOrProvince"] == "CO"
    assert result["StandardStatus"] == "Active"
    assert "ListPrice" not in result
    assert "BedroomsTotal" not in result


def test_map_listing_to_reso_with_description():
    addr = {"street": "456 Oak Rd", "city": "Portland", "state": "OR"}
    meta = {"description": "Beautiful home with modern finishes."}

    result = map_listing_to_reso(addr, meta)
    assert result["PublicRemarks"] == "Beautiful home with modern finishes."


def test_map_listing_property_type_variants():
    for raw, expected in [
        ("condo", "Residential Lease"),
        ("land", "Land"),
        ("commercial", "Commercial Sale"),
        ("unknown_type", "Residential"),  # defaults
    ]:
        result = map_listing_to_reso({}, {"property_type": raw})
        assert result["PropertyType"] == expected, f"Failed for {raw}"


def test_build_media_payload():
    payload = build_media_payload(
        photo_url="https://s3.example.com/photo.jpg",
        position=0,
        room_label="kitchen",
        caption="Modern open kitchen",
        is_hero=True,
    )

    assert payload["MediaURL"] == "https://s3.example.com/photo.jpg"
    assert payload["Order"] == 0
    assert payload["ImageOf"] == "kitchen"
    assert payload["PreferredPhotoYN"] is True
    assert payload["ShortDescription"] == "Modern open kitchen"


def test_build_media_payload_minimal():
    payload = build_media_payload("https://example.com/img.jpg", position=5)
    assert payload["Order"] == 5
    assert "ImageOf" not in payload
    assert "PreferredPhotoYN" not in payload


# --- Address Parsing Tests ---


def test_extract_street_number():
    assert _extract_street_number("123 Main St") == "123"
    assert _extract_street_number("12-34 Queens Blvd") == "12-34"
    assert _extract_street_number("Main Street") == ""


def test_extract_street_name():
    assert _extract_street_name("123 Main St") == "Main St"
    assert _extract_street_name("456 Elm Avenue NW") == "Elm Avenue NW"
    assert _extract_street_name("Oak Drive") == "Oak Drive"


# --- OAuth2 Token Tests ---


@pytest.mark.asyncio
async def test_oauth2_token_fetch():
    mock_client = MagicMock(spec=httpx.AsyncClient)

    # Token endpoint response
    mock_client.post = AsyncMock(
        return_value=_ok_response(
            {
                "access_token": "new-token-123",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        )
    )
    # Property request
    mock_client.request = AsyncMock(return_value=_ok_response({"value": []}))

    adapter = RESOAdapter(config=_make_config(), client=mock_client)
    await adapter.list_properties()

    # Verify token was fetched
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[0][0] == TOKEN_URL
    assert call_kwargs[1]["data"]["grant_type"] == "client_credentials"


@pytest.mark.asyncio
async def test_bearer_token_skips_oauth():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=_ok_response({"value": []}))

    config = _make_config(bearer_token="static-key-abc")
    adapter = RESOAdapter(config=config, client=mock_client)
    await adapter.list_properties()

    # Should NOT call the token endpoint
    mock_client.post.assert_not_called()
    # Should use the bearer token
    call_kwargs = mock_client.request.call_args
    assert "Bearer static-key-abc" in str(call_kwargs)


@pytest.mark.asyncio
async def test_from_legacy_constructor():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=_ok_response({"value": []}))

    adapter = RESOAdapter.from_legacy(BASE_URL, "api-key-123", client=mock_client)
    await adapter.list_properties()

    mock_client.post.assert_not_called()  # uses static bearer


# --- Property Submission Tests ---


@pytest.mark.asyncio
async def test_submit_property():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(
        return_value=_ok_response(
            {
                "ListingKey": "MLS-12345",
                "ListingId": "P-99",
            }
        )
    )

    config = _make_config(bearer_token="key")
    adapter = RESOAdapter(config=config, client=mock_client)
    result = await adapter.submit_property({"PropertyType": "Residential", "City": "Austin"})

    assert result["ListingKey"] == "MLS-12345"
    call_args = mock_client.request.call_args
    assert call_args[0][0] == "POST"
    assert "/Property" in call_args[0][1]


@pytest.mark.asyncio
async def test_submit_media():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=_ok_response({"status": "ok"}))

    config = _make_config(bearer_token="key")
    adapter = RESOAdapter(config=config, client=mock_client)

    payloads = [
        build_media_payload("https://s3.example.com/1.jpg", 0, is_hero=True),
        build_media_payload("https://s3.example.com/2.jpg", 1),
    ]
    result = await adapter.submit_media("MLS-12345", payloads)

    assert result["accepted"] == 2
    assert result["rejected"] == 0
    assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_submit_media_partial_failure():
    call_count = 0

    async def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise httpx.HTTPStatusError("Error", request=MagicMock(), response=_error_response(400))
        return _ok_response({"status": "ok"})

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(side_effect=_side_effect)

    config = _make_config(bearer_token="key")
    adapter = RESOAdapter(config=config, client=mock_client)

    payloads = [
        build_media_payload("https://s3.example.com/1.jpg", 0),
        build_media_payload("https://s3.example.com/2.jpg", 1),
        build_media_payload("https://s3.example.com/3.jpg", 2),
    ]
    result = await adapter.submit_media("MLS-X", payloads)

    assert result["accepted"] == 2
    assert result["rejected"] == 1
    assert len(result["errors"]) == 1


# --- Connection Test ---


@pytest.mark.asyncio
async def test_test_connection_success():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=_ok_response({}))

    config = _make_config(bearer_token="key")
    adapter = RESOAdapter(config=config, client=mock_client)
    result = await adapter.test_connection()

    assert result["status"] == "ok"
    assert "tested_at" in result


@pytest.mark.asyncio
async def test_test_connection_failure():
    mock_client = MagicMock(spec=httpx.AsyncClient)

    async def _fail(*args, **kwargs):
        raise RuntimeError("connection refused")

    mock_client.request = AsyncMock(side_effect=_fail)

    config = _make_config(bearer_token="key")
    adapter = RESOAdapter(config=config, client=mock_client, max_retries=1)
    result = await adapter.test_connection()

    assert result["status"] == "error"
    assert "connection refused" in result["error"]


# --- Retry Logic Tests ---


@pytest.mark.asyncio
async def test_retries_on_server_error():
    responses = [_error_response(500), _error_response(502), _ok_response({"value": []})]
    call_idx = 0

    async def _side_effect(*args, **kwargs):
        nonlocal call_idx
        resp = responses[call_idx]
        call_idx += 1
        resp.raise_for_status()
        return resp

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(side_effect=_side_effect)

    config = _make_config(bearer_token="key")
    adapter = RESOAdapter(config=config, client=mock_client, max_retries=3)
    result = await adapter.list_properties()

    assert result == []
    assert call_idx == 3


@pytest.mark.asyncio
async def test_no_retry_on_4xx():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    resp = _error_response(404)
    mock_client.request = AsyncMock(return_value=resp)

    config = _make_config(bearer_token="key")
    adapter = RESOAdapter(config=config, client=mock_client, max_retries=3)

    with pytest.raises(httpx.HTTPStatusError):
        await adapter.list_properties()

    assert mock_client.request.call_count == 1
