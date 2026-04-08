# src/listingjet/services/reso_adapter.py
"""
RESO Web API v2 adapter — OAuth2 auth, Data Dictionary field mapping,
property submission, and media upload for one-click MLS publish.

Implements the RESO Web API standard (https://www.reso.org/reso-web-api/).
Uses OAuth2 client_credentials flow per RESO transport specification.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RESO Data Dictionary v2.0 field mapping
# Maps LaunchLens internal fields → RESO standard resource names
# ---------------------------------------------------------------------------
_PROPERTY_TYPE_MAP: dict[str, str] = {
    "single_family": "Residential",
    "single-family": "Residential",
    "house": "Residential",
    "condo": "Residential Lease",
    "townhouse": "Residential",
    "multi_family": "Residential Income",
    "multi-family": "Residential Income",
    "land": "Land",
    "commercial": "Commercial Sale",
}


def map_listing_to_reso(listing_address: dict, listing_metadata: dict) -> dict:
    """Convert LaunchLens listing data to a RESO Data Dictionary Property resource.

    Returns a dict ready to POST to /Property per RESO Web API v2.
    """
    addr = listing_address or {}
    meta = listing_metadata or {}

    prop_type_raw = (meta.get("property_type") or "").lower().strip()
    reso_property_type = _PROPERTY_TYPE_MAP.get(prop_type_raw, "Residential")

    reso_payload: dict = {
        # Required fields
        "PropertyType": reso_property_type,
        "StandardStatus": "Active",
        "MlsStatus": "Active",
        # Address fields (RESO Data Dictionary)
        "StreetNumber": _extract_street_number(addr.get("street", "")),
        "StreetName": _extract_street_name(addr.get("street", "")),
        "StreetSuffix": "",
        "City": addr.get("city", ""),
        "StateOrProvince": addr.get("state", ""),
        "PostalCode": addr.get("zip", ""),
        "Country": addr.get("country", "US"),
    }

    if addr.get("unit"):
        reso_payload["UnitNumber"] = addr["unit"]

    # Numeric fields — only include if present
    if meta.get("price") is not None:
        reso_payload["ListPrice"] = meta["price"]

    beds = meta.get("beds") or meta.get("bedrooms")
    if beds is not None:
        reso_payload["BedroomsTotal"] = int(beds)

    baths = meta.get("baths") or meta.get("bathrooms")
    if baths is not None:
        reso_payload["BathroomsTotalInteger"] = int(baths)
        # RESO also supports BathroomsFull + BathroomsHalf
        if isinstance(baths, float) and baths != int(baths):
            reso_payload["BathroomsFull"] = int(baths)
            reso_payload["BathroomsHalf"] = 1

    sqft = meta.get("sqft")
    if sqft is not None:
        reso_payload["LivingArea"] = sqft
        reso_payload["LivingAreaUnits"] = "Square Feet"

    lot_sqft = meta.get("lot_sqft")
    if lot_sqft is not None:
        reso_payload["LotSizeSquareFeet"] = lot_sqft

    year_built = meta.get("year_built")
    if year_built is not None:
        reso_payload["YearBuilt"] = year_built

    # Description (MLS-safe version)
    description = meta.get("description")
    if description:
        reso_payload["PublicRemarks"] = description[:4000]  # RESO max length

    return reso_payload


def build_media_payload(
    photo_url: str,
    position: int,
    room_label: str = "",
    caption: str = "",
    is_hero: bool = False,
) -> dict:
    """Build a RESO Media Resource payload for a single photo."""
    media: dict = {
        "MediaURL": photo_url,
        "MediaType": "image/jpeg",
        "Order": position,
        "MediaCategory": "Photo",
        "ShortDescription": caption[:255] if caption else "",
    }
    if room_label:
        media["ImageOf"] = room_label
    if is_hero:
        media["PreferredPhotoYN"] = True
    return media


# ---------------------------------------------------------------------------
# OAuth2 token management
# ---------------------------------------------------------------------------
@dataclass
class _TokenCache:
    access_token: str = ""
    expires_at: float = 0.0  # unix timestamp

    @property
    def is_valid(self) -> bool:
        return bool(self.access_token) and time.time() < (self.expires_at - 30)


# ---------------------------------------------------------------------------
# RESOAdapter — full-featured async client
# ---------------------------------------------------------------------------
@dataclass
class RESOConnectionConfig:
    """Connection parameters for a single MLS board."""

    base_url: str
    oauth_token_url: str
    client_id: str
    client_secret: str
    bearer_token: str | None = None  # static token fallback
    extra_headers: dict = field(default_factory=dict)


class RESOAdapter:
    """Async RESO Web API v2 client with OAuth2 and retry support."""

    def __init__(
        self,
        config: RESOConnectionConfig,
        client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
    ):
        self._config = config
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._token_cache = _TokenCache()
        self._max_retries = max_retries

    @classmethod
    def from_legacy(cls, base_url: str, api_key: str, **kwargs) -> "RESOAdapter":
        """Backward-compatible constructor from old (base_url, api_key) interface."""
        config = RESOConnectionConfig(
            base_url=base_url,
            oauth_token_url="",
            client_id="",
            client_secret="",
            bearer_token=api_key,
        )
        return cls(config=config, **kwargs)

    # -- Auth ---------------------------------------------------------------

    async def _get_access_token(self) -> str:
        """Obtain or refresh an OAuth2 access token via client_credentials grant."""
        if self._config.bearer_token:
            return self._config.bearer_token

        if self._token_cache.is_valid:
            return self._token_cache.access_token

        if not self._config.oauth_token_url:
            raise RuntimeError("No OAuth token URL configured and no static bearer token")

        response = await self._client.post(
            self._config.oauth_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "scope": "api",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        token_data = response.json()

        self._token_cache = _TokenCache(
            access_token=token_data["access_token"],
            expires_at=time.time() + token_data.get("expires_in", 3600),
        )
        logger.info("reso_oauth2_token_refreshed board=%s", self._config.base_url)
        return self._token_cache.access_token

    async def _auth_headers(self) -> dict[str, str]:
        token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            **self._config.extra_headers,
        }
        return headers

    # -- Low-level HTTP with retry -----------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | list | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                headers = await self._auth_headers()
                response = await self._client.request(method, url, json=json, params=params, headers=headers)
                # 401 → token may be stale, clear cache and retry once
                if response.status_code == 401 and attempt == 1:
                    self._token_cache = _TokenCache()
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code
                # Don't retry 4xx (except 401 handled above, 429)
                if 400 <= status < 500 and status != 429:
                    raise
                logger.warning(
                    "reso_request_retry attempt=%d/%d status=%s path=%s",
                    attempt,
                    self._max_retries,
                    status,
                    path,
                )
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning(
                    "reso_request_error attempt=%d/%d error=%s path=%s",
                    attempt,
                    self._max_retries,
                    exc,
                    path,
                )

        raise RuntimeError(f"RESO API request failed after {self._max_retries} attempts: {last_exc}") from last_exc

    # -- RESO Web API operations -------------------------------------------

    async def test_connection(self) -> dict:
        """Test connectivity by fetching the RESO service metadata endpoint."""
        try:
            response = await self._request("GET", "/$metadata")
            return {
                "status": "ok",
                "response_code": response.status_code,
                "tested_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc)[:500],
                "tested_at": datetime.now(timezone.utc).isoformat(),
            }

    async def list_properties(self, filters: dict | None = None) -> list[dict]:
        """GET /Property with optional OData-style query filters."""
        response = await self._request("GET", "/Property", params=filters)
        return response.json().get("value", [])

    async def get_property(self, property_id: str) -> dict:
        """GET /Property('{property_id}')."""
        response = await self._request("GET", f"/Property('{property_id}')")
        return response.json()

    async def submit_property(self, reso_payload: dict) -> dict:
        """POST /Property — create a new listing on the MLS.

        Returns the RESO response containing the assigned ListingKey.
        """
        response = await self._request("POST", "/Property", json=reso_payload)
        result = response.json()
        logger.info(
            "reso_property_submitted listing_key=%s",
            result.get("ListingKey", "unknown"),
        )
        return result

    async def update_property(self, listing_key: str, updates: dict) -> dict:
        """PATCH /Property('{listing_key}') — update an existing listing."""
        response = await self._request("PATCH", f"/Property('{listing_key}')", json=updates)
        if response.status_code == 204:
            return {"status": "updated", "ListingKey": listing_key}
        return response.json()

    async def submit_media(self, listing_key: str, media_payloads: list[dict]) -> dict:
        """POST /Media for each photo in the media payload list.

        Returns summary of accepted/rejected media items.
        """
        accepted = 0
        rejected = 0
        errors: list[dict] = []

        for payload in media_payloads:
            # Add the ListingKey reference
            payload["ResourceRecordKey"] = listing_key
            payload["ResourceName"] = "Property"
            try:
                await self._request("POST", "/Media", json=payload)
                accepted += 1
            except Exception as exc:
                rejected += 1
                errors.append(
                    {
                        "order": payload.get("Order", -1),
                        "error": str(exc)[:300],
                    }
                )
                logger.warning(
                    "reso_media_submit_failed listing_key=%s order=%s error=%s",
                    listing_key,
                    payload.get("Order"),
                    exc,
                )

        return {
            "listing_key": listing_key,
            "accepted": accepted,
            "rejected": rejected,
            "errors": errors,
        }

    async def submit_photos(self, property_id: str, photo_urls: list[str]) -> dict:
        """Legacy interface — submit photos by URL list."""
        media_payloads = [build_media_payload(url, position=i) for i, url in enumerate(photo_urls)]
        return await self.submit_media(property_id, media_payloads)

    async def get_listing_status(self, listing_key: str) -> dict:
        """Check the current status of a submitted listing."""
        result = await self.get_property(listing_key)
        return {
            "ListingKey": result.get("ListingKey"),
            "StandardStatus": result.get("StandardStatus"),
            "MlsStatus": result.get("MlsStatus"),
            "ModificationTimestamp": result.get("ModificationTimestamp"),
        }


# ---------------------------------------------------------------------------
# Address parsing helpers
# ---------------------------------------------------------------------------


def _extract_street_number(street: str) -> str:
    """Extract the leading numeric portion from a street string."""
    parts = street.strip().split(None, 1)
    if parts and parts[0].replace("-", "").isdigit():
        return parts[0]
    return ""


def _extract_street_name(street: str) -> str:
    """Extract the street name (everything after the number)."""
    parts = street.strip().split(None, 1)
    if len(parts) >= 2 and parts[0].replace("-", "").isdigit():
        return parts[1]
    return street.strip()
