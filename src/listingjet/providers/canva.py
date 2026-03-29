# src/listingjet/providers/canva.py
"""Canva Connect API template provider.

Capabilities:
- Autofill brand templates with listing data, brand kit, and hero photo
- Poll async jobs (autofill, export)
- Export designs as PDF
- Upload hero photos as Canva assets for template placement
"""
import logging

import httpx

from .base import TemplateProvider

logger = logging.getLogger(__name__)

_CANVA_API_BASE = "https://api.canva.com/rest/v1"


class CanvaTemplateProvider(TemplateProvider):
    """Renders listing flyers via the Canva Connect API."""

    def __init__(self, api_key: str, llm_provider=None):
        self._api_key = api_key
        self._llm = llm_provider

    async def render(self, template_id: str, data: dict) -> bytes:
        """
        Autofill a Canva brand template with listing + brand data, export as PDF.

        Steps:
        1. Upload hero photo as Canva asset (if hero_image_url provided)
        2. POST /autofills — autofill the template with all data fields
        3. Poll until autofill job completes
        4. POST /exports — request PDF export
        5. Poll until export completes, download PDF bytes
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(base_url=_CANVA_API_BASE, timeout=60) as client:
            # 1. Upload hero photo as Canva asset if URL provided
            hero_asset_id = None
            if data.get("hero_image_url"):
                hero_asset_id = await self._upload_hero_asset(
                    client, headers, data["hero_image_url"]
                )

            # 2. Start autofill
            autofill_fields = _build_autofill_data(data, hero_asset_id)
            autofill_resp = await client.post(
                "/autofills",
                headers=headers,
                json={
                    "brand_template_id": template_id,
                    "data": autofill_fields,
                },
            )
            autofill_resp.raise_for_status()
            autofill_job = autofill_resp.json()["job"]
            design_id = await _poll_job(
                client, headers, f"/autofills/{autofill_job['id']}", "design_id"
            )

            # 3. Export as PDF
            export_resp = await client.post(
                "/exports",
                headers=headers,
                json={"design_id": design_id, "format": "pdf"},
            )
            export_resp.raise_for_status()
            export_job = export_resp.json()["job"]
            pdf_url = await _poll_job(
                client, headers, f"/exports/{export_job['id']}", "url"
            )

            # 4. Download the rendered PDF
            pdf_resp = await client.get(pdf_url)
            pdf_resp.raise_for_status()
            return pdf_resp.content

    async def _upload_hero_asset(
        self, client: httpx.AsyncClient, headers: dict, image_url: str
    ) -> str | None:
        """Upload a hero photo URL as a Canva asset. Returns asset ID or None on failure."""
        try:
            resp = await client.post(
                "/asset-uploads",
                headers=headers,
                json={"url": image_url},
            )
            resp.raise_for_status()
            job = resp.json().get("job", {})
            asset_id = await _poll_job(
                client, headers, f"/asset-uploads/{job['id']}", "asset_id",
                max_attempts=10, delay_s=1.5,
            )
            return asset_id
        except Exception:
            logger.warning("canva.hero_upload_failed url=%s", image_url, exc_info=True)
            return None


async def _poll_job(
    client: httpx.AsyncClient,
    headers: dict,
    path: str,
    result_key: str,
    max_attempts: int = 20,
    delay_s: float = 2.0,
) -> str:
    """Poll a Canva async job until it succeeds; return the value at result_key."""
    import asyncio

    for _ in range(max_attempts):
        resp = await client.get(path, headers=headers)
        resp.raise_for_status()
        job = resp.json()["job"]
        status = job.get("status")
        if status == "success":
            return job["result"][result_key]
        if status == "failed":
            raise RuntimeError(f"Canva job failed: {job}")
        await asyncio.sleep(delay_s)
    raise TimeoutError(f"Canva job at {path} did not complete in time")


def _build_autofill_data(data: dict, hero_asset_id: str | None = None) -> list[dict]:
    """Convert listing + brand data into Canva autofill field objects."""
    fields = []

    # Property fields
    _add_text(fields, "property_address", _format_address(data.get("address", {})))
    _add_text(fields, "listing_price", _format_price(data.get("metadata", {})))
    _add_text(fields, "bedrooms", str(data.get("metadata", {}).get("beds", "")))
    _add_text(fields, "bathrooms", str(data.get("metadata", {}).get("baths", "")))
    _add_text(fields, "square_footage", _format_sqft(data.get("metadata", {})))
    _add_text(fields, "property_description", data.get("description", ""))

    # Brand fields
    _add_text(fields, "agent_name", data.get("agent_name", ""))
    _add_text(fields, "brokerage_name", data.get("brokerage_name", ""))
    _add_text(fields, "primary_color", data.get("primary_color", ""))

    # Hero image — either as Canva asset or external URL
    if hero_asset_id:
        fields.append({
            "name": "hero_image",
            "value": {"type": "image", "asset_id": hero_asset_id},
        })
    elif data.get("hero_image_url"):
        _add_text(fields, "hero_image_url", data["hero_image_url"])

    # Logo
    if data.get("logo_url"):
        _add_text(fields, "logo_url", data["logo_url"])

    return fields


def _add_text(fields: list, name: str, value: str) -> None:
    """Append a text field only if value is non-empty."""
    if value:
        fields.append({"name": name, "value": {"type": "text", "text": value}})


def _format_address(address: dict) -> str:
    parts = [address.get("street", "")]
    city_state = ", ".join(filter(None, [address.get("city"), address.get("state")]))
    if city_state:
        parts.append(city_state)
    zipcode = address.get("zip", "")
    if zipcode:
        parts.append(zipcode)
    return " ".join(filter(None, parts))


def _format_price(metadata: dict) -> str:
    price = metadata.get("price")
    if price:
        return f"${price:,.0f}" if isinstance(price, (int, float)) else str(price)
    return ""


def _format_sqft(metadata: dict) -> str:
    sqft = metadata.get("sqft")
    if sqft:
        return f"{sqft:,}" if isinstance(sqft, (int, float)) else str(sqft)
    return ""
