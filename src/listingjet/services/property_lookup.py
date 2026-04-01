"""
Property lookup service using ATTOM Data + Walk Score APIs.

Fetches property details and neighborhood scores for a given address,
with in-memory caching and automatic retry using alternate address forms.
"""

import logging
import time

import httpx

from listingjet.api.schemas.properties import (
    CoreFields,
    DetailFields,
    NeighborhoodFields,
    PropertyLookupResponse,
)
from listingjet.config import settings
from listingjet.services.address_normalizer import address_hash, generate_alternates

logger = logging.getLogger(__name__)

# ATTOM proptype → normalized property_type
_PROP_TYPE_MAP: dict[str, str] = {
    "SFR": "single_family",
    "CONDO": "condo",
    "TOWNHOUSE": "townhouse",
    "MOBILE": "mobile",
    "MULTI-FAMILY": "multi_family",
    "COOP": "coop",
    "LAND": "land",
}


def _safe_int(value: object) -> int | None:
    """Convert a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


class PropertyLookupService:
    """Fetches property data from ATTOM and neighborhood scores from Walk Score."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, PropertyLookupResponse]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def lookup(self, address: str) -> PropertyLookupResponse:
        """Look up property details and neighborhood scores for *address*."""
        cache_key = address_hash(address)

        # Check cache
        cached = self._cache.get(cache_key)
        if cached is not None:
            ts, response = cached
            if time.time() - ts < settings.property_lookup_cache_ttl:
                return response

        # ATTOM lookup
        attom_data = await self._call_attom(address)
        props = attom_data.get("property", [])

        # Retry with alternates if empty
        if not props:
            alternates = generate_alternates(address)
            for alt in alternates:
                attom_data = await self._call_attom(alt)
                props = attom_data.get("property", [])
                if props:
                    break

        # Parse ATTOM
        found = bool(props)
        core = CoreFields()
        details = DetailFields()
        if found:
            core, details = self._parse_attom(props[0])

        # Walk Score lookup
        ws_data = await self._call_walkscore(address)
        neighborhood = self._parse_walkscore(ws_data)

        response = PropertyLookupResponse(
            source="attom+walkscore",
            found=found,
            core=core,
            details=details,
            neighborhood=neighborhood,
        )

        # Cache
        self._cache[cache_key] = (time.time(), response)
        return response

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _call_attom(self, address: str) -> dict:
        """GET ATTOM basic-profile endpoint. Returns raw JSON or empty on error."""
        if not settings.attom_api_key:
            return {"property": []}

        url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/basicprofile"
        params = {"address": address}
        headers = {"apikey": settings.attom_api_key}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except Exception:
            logger.exception("ATTOM API call failed for %s", address)
            return {"property": []}

    async def _call_walkscore(self, address: str) -> dict:
        """GET Walk Score endpoint. Returns raw JSON or empty dict on error."""
        if not settings.walk_score_api_key:
            return {}

        url = "https://api.walkscore.com/score"
        params = {
            "format": "json",
            "address": address,
            "transit": 1,
            "bike": 1,
            "wsapikey": settings.walk_score_api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception:
            logger.exception("Walk Score API call failed for %s", address)
            return {}

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_attom(prop: dict) -> tuple[CoreFields, DetailFields]:
        """Extract CoreFields and DetailFields from a single ATTOM property dict."""
        building = prop.get("building", {})
        rooms = building.get("rooms", {})
        size = building.get("size", {})
        summary = building.get("summary", {})
        lot = prop.get("lot", {})

        raw_type = str(summary.get("proptype", "")).upper()
        property_type = _PROP_TYPE_MAP.get(raw_type)

        core = CoreFields(
            beds=_safe_int(rooms.get("beds")),
            baths=_safe_int(rooms.get("bathsfull")),
            half_baths=_safe_int(rooms.get("bathshalf")),
            sqft=_safe_int(size.get("livingsize")),
            lot_sqft=_safe_int(lot.get("lotsize2")),
            year_built=_safe_int(summary.get("yearbuilt")),
        )

        details = DetailFields(
            property_type=property_type,
        )

        return core, details

    @staticmethod
    def _parse_walkscore(data: dict) -> NeighborhoodFields:
        """Extract NeighborhoodFields from Walk Score response."""
        transit = data.get("transit", {})
        bike = data.get("bike", {})

        return NeighborhoodFields(
            walk_score=_safe_int(data.get("walkscore")),
            transit_score=_safe_int(transit.get("score")) if transit else None,
            bike_score=_safe_int(bike.get("score")) if bike else None,
        )
