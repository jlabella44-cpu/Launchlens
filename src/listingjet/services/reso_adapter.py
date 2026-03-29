# src/listingjet/services/reso_adapter.py
"""
RESO Web API adapter — list, fetch, and update MLS property data.
"""
from __future__ import annotations

import httpx


class RESOAdapter:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = client or httpx.AsyncClient()

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def list_properties(self, filters: dict | None = None) -> list[dict]:
        """GET /Property with optional OData-style query filters."""
        url = f"{self._base_url}/Property"
        try:
            response = await self._client.get(
                url, params=filters, headers=self._headers
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"RESO list_properties failed with status {exc.response.status_code}"
            ) from exc
        return response.json().get("value", [])

    async def get_property(self, property_id: str) -> dict:
        """GET /Property('{property_id}')."""
        url = f"{self._base_url}/Property('{property_id}')"
        try:
            response = await self._client.get(url, headers=self._headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"RESO get_property failed with status {exc.response.status_code}"
            ) from exc
        return response.json()

    async def submit_photos(
        self, property_id: str, photo_urls: list[str]
    ) -> dict:
        """POST photos to /Property('{property_id}')/Media."""
        url = f"{self._base_url}/Property('{property_id}')/Media"
        try:
            response = await self._client.post(
                url, json=photo_urls, headers=self._headers
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"RESO submit_photos failed with status {exc.response.status_code}"
            ) from exc
        return response.json()
