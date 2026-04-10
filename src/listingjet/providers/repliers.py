# src/listingjet/providers/repliers.py
"""
Repliers provider — MLS data aggregator (https://docs.repliers.io).

Used by services/comparables.py to fetch real comparable sales for CMA reports.
Repliers pricing is per-MLS-system licensed, so calls are feature-flagged via
`settings.repliers_cma_enabled` and gracefully degrade when the flag is off or
the API key is missing.

Only the endpoints we actually need are implemented:
  - search_listings(filters)          — GET /listings with filter params
  - get_similar(mls_number, limit)    — GET /listings/{mlsNumber}/similar
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from listingjet.config import settings
from listingjet.services.metrics import record_provider_call

logger = logging.getLogger(__name__)

# Repliers API returns listings under a top-level "listings" key; each record
# has a nested shape like:
# {
#   "mlsNumber": "C1234567",
#   "listPrice": 850000,
#   "soldPrice": 835000,
#   "address": {"streetNumber": "123", "streetName": "Oak", "streetSuffix": "Ave",
#               "city": "Austin", "state": "TX", "zip": "78701"},
#   "details": {"numBedrooms": 3, "numBathrooms": 2, "sqft": 1800, "yearBuilt": 2010,
#                "propertyType": "Residential"},
#   "soldDate": "2024-11-04",
#   "status": "Sld",
#   ...
# }
# We normalize this to a dict shape the CMA agent already understands.


class RepliersClient:
    """Thin async wrapper around the Repliers REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ):
        self._api_key = api_key if api_key is not None else settings.repliers_api_key
        self._base_url = (base_url or settings.repliers_api_base).rstrip("/")
        self._timeout = timeout or settings.repliers_timeout_seconds

    @property
    def configured(self) -> bool:
        """True if the client has an API key and can make real calls."""
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "REPLIERS-API-KEY": self._api_key,
            "Accept": "application/json",
        }

    async def search_listings(self, filters: dict[str, Any]) -> list[dict]:
        """GET /listings with the given filter params.

        Typical filters for comparables lookup:
            {
              "status": "Sld",            # sold only
              "minBedrooms": 2,
              "maxBedrooms": 4,
              "minSqft": 1600,
              "maxSqft": 2000,
              "city": "Austin",
              "state": "TX",
              "soldSince": "2024-01-01",  # last 12 months
              "pageSize": 10,
            }
        """
        if not self.configured:
            return []

        url = f"{self._base_url}/listings"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, params=filters, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                record_provider_call("repliers", True)
                return data.get("listings", []) or []
        except Exception:
            logger.warning("repliers.search_listings failed filters=%s", filters)
            record_provider_call("repliers", False)
            return []

    async def get_similar(self, mls_number: str, limit: int = 10) -> list[dict]:
        """GET /listings/{mlsNumber}/similar — comparable listings for a known MLS #."""
        if not self.configured:
            return []

        url = f"{self._base_url}/listings/{mls_number}/similar"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    url,
                    params={"pageSize": limit},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                record_provider_call("repliers", True)
                return data.get("listings", []) or []
        except Exception:
            logger.warning("repliers.get_similar failed mls=%s", mls_number)
            record_provider_call("repliers", False)
            return []


def normalize_listing(raw: dict) -> dict | None:
    """Convert a raw Repliers listing into the dict shape CMAReportAgent expects.

    Returns None if the listing is missing essential fields (price + sqft).
    """
    details = raw.get("details") or {}
    address = raw.get("address") or {}

    # Prefer sold price → close price → list price
    price = raw.get("soldPrice") or raw.get("closePrice") or raw.get("listPrice")
    sqft = details.get("sqft") or details.get("squareFeet")
    if not price or not sqft:
        return None

    try:
        price_int = int(float(price))
        sqft_int = int(float(sqft))
    except (ValueError, TypeError):
        return None

    if sqft_int <= 0:
        return None

    beds = details.get("numBedrooms") or details.get("beds")
    baths = details.get("numBathrooms") or details.get("baths")

    street_parts = [
        address.get("streetNumber"),
        address.get("streetName"),
        address.get("streetSuffix"),
    ]
    street = " ".join(str(p).strip() for p in street_parts if p)
    city = address.get("city", "")
    full_address = f"{street}, {city}".strip(", ")

    return {
        "address": full_address or "—",
        "beds": int(beds) if beds is not None else None,
        "baths": float(baths) if baths is not None else None,
        "sqft": sqft_int,
        "price": price_int,
        "price_per_sqft": round(price_int / sqft_int, 2),
        "sold_date": raw.get("soldDate") or raw.get("closeDate"),
        "mls_number": raw.get("mlsNumber"),
    }
