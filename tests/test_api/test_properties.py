"""Property lookup API endpoint tests."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from listingjet.api.schemas.properties import (
    CoreFields,
    DetailFields,
    NeighborhoodFields,
    PropertyLookupResponse,
)


async def _register(client: AsyncClient) -> str:
    resp = await client.post("/auth/register", json={
        "email": f"prop-{uuid.uuid4()}@example.com",
        "password": "TestPass1!", "name": "PropTester", "company_name": "PropCo"
    })
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# 1. Auth required

@pytest.mark.asyncio
async def test_lookup_requires_auth(async_client: AsyncClient):
    """GET /properties/lookup without a token returns 401 or 403."""
    resp = await async_client.get("/properties/lookup", params={"address": "123 Main St, Denver, CO"})
    assert resp.status_code in (401, 403)


# 2. address param required

@pytest.mark.asyncio
async def test_lookup_requires_address_param(async_client: AsyncClient):
    """GET /properties/lookup without address query param returns 422."""
    token = await _register(async_client)
    resp = await async_client.get("/properties/lookup", headers=_auth(token))
    assert resp.status_code == 422


# 3. Successful lookup

@pytest.mark.asyncio
async def test_lookup_returns_property_data(async_client: AsyncClient):
    """Mock PropertyLookupService.lookup returns known data; verify response shape."""
    token = await _register(async_client)

    mock_response = PropertyLookupResponse(
        source="attom+walkscore",
        found=True,
        core=CoreFields(beds=3, baths=2, sqft=1800, year_built=2005),
        details=DetailFields(property_type="single_family"),
        neighborhood=NeighborhoodFields(walk_score=72, transit_score=45, bike_score=60),
    )

    mock_svc = MagicMock()
    mock_svc.lookup = AsyncMock(return_value=mock_response)

    with patch("listingjet.api.properties.PropertyLookupService", return_value=mock_svc):
        resp = await async_client.get(
            "/properties/lookup",
            params={"address": "123 Main St, Denver, CO"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert body["source"] == "attom+walkscore"
    assert body["core"]["beds"] == 3
    assert body["core"]["baths"] == 2
    assert body["core"]["sqft"] == 1800
    assert body["core"]["year_built"] == 2005
    assert body["details"]["property_type"] == "single_family"
    assert body["neighborhood"]["walk_score"] == 72
    assert body["neighborhood"]["transit_score"] == 45
    assert body["neighborhood"]["bike_score"] == 60


# 4. Not found

@pytest.mark.asyncio
async def test_lookup_not_found(async_client: AsyncClient):
    """Mock PropertyLookupService.lookup returns found=False; verify response."""
    token = await _register(async_client)

    mock_response = PropertyLookupResponse(
        source="attom+walkscore",
        found=False,
    )

    mock_svc = MagicMock()
    mock_svc.lookup = AsyncMock(return_value=mock_response)

    with patch("listingjet.api.properties.PropertyLookupService", return_value=mock_svc):
        resp = await async_client.get(
            "/properties/lookup",
            params={"address": "99999 Nowhere Blvd, Unknown, ZZ"},
            headers=_auth(token),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["source"] == "attom+walkscore"
