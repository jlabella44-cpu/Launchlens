# src/listingjet/providers/canva.py
"""Canva Connect API template provider.

Capabilities:
- Autofill brand templates with listing data, brand kit, and hero photo
- Poll async jobs (autofill, export, asset upload) via a thin httpx client
- Export designs as PDF
- Upload hero photos as Canva assets for template placement
"""
import asyncio
import logging

from .base import TemplateProvider
from .canva_client import CanvaClient

logger = logging.getLogger(__name__)

_CANVA_API_BASE = "https://api.canva.com/rest"


class CanvaTemplateProvider(TemplateProvider):
    """Renders listing flyers via the Canva Connect API."""

    def __init__(self, api_key: str, llm_provider=None, access_token: str | None = None):
        self._api_key = api_key
        self._llm = llm_provider
        self._access_token = access_token

    @property
    def _effective_token(self) -> str:
        """Per-tenant OAuth token takes priority; fall back to global API key."""
        return self._access_token or self._api_key

    async def render(self, template_id: str, data: dict) -> bytes:
        """
        Autofill a Canva brand template with listing + brand data, export as PDF.

        Steps:
        1. Upload hero photo as Canva asset (if hero_image_url provided)
        2. Create autofill job with the template and all data fields
        3. Poll until autofill job completes
        4. Create export job for PDF
        5. Poll until export completes, download PDF bytes
        """
        async with CanvaClient(token=self._effective_token, base_url=_CANVA_API_BASE) as client:
            # 1. Upload hero photo as Canva asset if URL provided
            hero_asset_id = None
            if data.get("hero_image_url"):
                hero_asset_id = await self._upload_hero_asset(
                    client, data["hero_image_url"]
                )

            # 2. Start autofill
            autofill_data = _build_autofill_data(data, hero_asset_id)
            job_id = await client.create_autofill(template_id, autofill_data)

            # 3. Poll autofill until done
            design_id = await _poll_autofill(client, job_id)

            # 4. Export as PDF
            export_job_id = await client.create_export(design_id, {"type": "pdf"})

            # 5. Poll export until done
            pdf_url = await _poll_export(client, export_job_id)

            # 6. Download the rendered PDF
            return await client.download(pdf_url)

    async def _upload_hero_asset(
        self, client: CanvaClient, image_url: str
    ) -> str | None:
        """Upload a hero photo URL as a Canva asset. Returns asset ID or None on failure."""
        try:
            job_id = await client.create_url_asset_upload("hero_image", image_url)
            return await _poll_upload(client, job_id)
        except Exception:
            logger.warning("canva.hero_upload_failed url=%s", image_url, exc_info=True)
            return None


async def _poll_autofill(
    client: CanvaClient,
    job_id: str,
    max_attempts: int = 20,
    delay_s: float = 2.0,
) -> str:
    """Poll autofill job until success; return the design ID."""
    for _ in range(max_attempts):
        result = await client.get_autofill(job_id)
        if result["status"] == "success":
            return result["design_id"]
        if result["status"] == "failed":
            raise RuntimeError(f"Canva autofill job failed: {result}")
        await asyncio.sleep(delay_s)
    raise TimeoutError(f"Canva autofill job {job_id} did not complete in time")


async def _poll_export(
    client: CanvaClient,
    export_id: str,
    max_attempts: int = 20,
    delay_s: float = 2.0,
) -> str:
    """Poll export job until success; return the first download URL."""
    for _ in range(max_attempts):
        result = await client.get_export(export_id)
        if result["status"] == "success":
            return result["urls"][0]
        if result["status"] == "failed":
            raise RuntimeError(f"Canva export job failed: {result}")
        await asyncio.sleep(delay_s)
    raise TimeoutError(f"Canva export job {export_id} did not complete in time")


async def _poll_upload(
    client: CanvaClient,
    job_id: str,
    max_attempts: int = 10,
    delay_s: float = 1.5,
) -> str:
    """Poll URL asset upload job until success; return the asset ID."""
    for _ in range(max_attempts):
        result = await client.get_url_asset_upload(job_id)
        if result["status"] == "success":
            return result["asset_id"]
        if result["status"] == "failed":
            raise RuntimeError(f"Canva upload job failed: {result}")
        await asyncio.sleep(delay_s)
    raise TimeoutError(f"Canva upload job {job_id} did not complete in time")


def _build_autofill_data(
    data: dict, hero_asset_id: str | None = None
) -> dict:
    """Convert listing + brand data into Canva autofill request data.

    Returns a plain dict of field_name -> {"type": "text"|"image", ...}
    matching the Canva autofill API's JSON shape directly.
    """
    fields: dict[str, dict] = {}

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
        fields["hero_image"] = {"type": "image", "asset_id": hero_asset_id}
    elif data.get("hero_image_url"):
        _add_text(fields, "hero_image_url", data["hero_image_url"])

    # Logo
    if data.get("logo_url"):
        _add_text(fields, "logo_url", data["logo_url"])

    return fields


def _add_text(fields: dict, name: str, value: str) -> None:
    """Add a text field only if value is non-empty."""
    if value:
        fields[name] = {"type": "text", "text": value}


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
