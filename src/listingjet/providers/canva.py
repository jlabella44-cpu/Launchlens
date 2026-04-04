# src/listingjet/providers/canva.py
"""Canva Connect API template provider.

Capabilities:
- Autofill brand templates with listing data, brand kit, and hero photo
- Poll async jobs (autofill, export, asset upload) via generated client
- Export designs as PDF
- Upload hero photos as Canva assets for template placement
"""
import asyncio
import logging
from http import HTTPStatus

import httpx

from .base import TemplateProvider
from .canva_generated.canva_connect_api_client.api.asset import (
    create_url_asset_upload_job,
    get_url_asset_upload_job,
)
from .canva_generated.canva_connect_api_client.api.autofill import (
    create_design_autofill_job,
    get_design_autofill_job,
)
from .canva_generated.canva_connect_api_client.api.export import (
    create_design_export_job,
    get_design_export_job,
)
from .canva_generated.canva_connect_api_client.client import AuthenticatedClient
from .canva_generated.canva_connect_api_client.models.create_design_autofill_job_request import (
    CreateDesignAutofillJobRequest,
)
from .canva_generated.canva_connect_api_client.models.create_design_autofill_job_request_data import (
    CreateDesignAutofillJobRequestData,
)
from .canva_generated.canva_connect_api_client.models.create_design_export_job_request import (
    CreateDesignExportJobRequest,
)
from .canva_generated.canva_connect_api_client.models.create_url_asset_upload_job_request import (
    CreateUrlAssetUploadJobRequest,
)
from .canva_generated.canva_connect_api_client.models.error import Error
from .canva_generated.canva_connect_api_client.models.pdf_export_format import PdfExportFormat
from .canva_generated.canva_connect_api_client.models.pdf_export_format_type import PdfExportFormatType

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
        client = AuthenticatedClient(
            base_url=_CANVA_API_BASE,
            token=self._effective_token,
            timeout=httpx.Timeout(60.0),
        )

        async with client:
            # 1. Upload hero photo as Canva asset if URL provided
            hero_asset_id = None
            if data.get("hero_image_url"):
                hero_asset_id = await self._upload_hero_asset(
                    client, data["hero_image_url"]
                )

            # 2. Start autofill
            autofill_data = _build_autofill_data(data, hero_asset_id)
            autofill_body = CreateDesignAutofillJobRequest(
                brand_template_id=template_id,
                data=autofill_data,
            )
            autofill_resp = await create_design_autofill_job.asyncio_detailed(
                client=client, body=autofill_body,
            )
            if autofill_resp.status_code != HTTPStatus.OK or isinstance(autofill_resp.parsed, Error):
                raise RuntimeError(f"Canva autofill request failed: {autofill_resp.status_code}")
            job_id = autofill_resp.parsed.job.id

            # 3. Poll autofill until done
            design_id = await _poll_autofill(client, job_id)

            # 4. Export as PDF
            export_body = CreateDesignExportJobRequest(
                design_id=design_id,
                format_=PdfExportFormat(type_=PdfExportFormatType.PDF),
            )
            export_resp = await create_design_export_job.asyncio_detailed(
                client=client, body=export_body,
            )
            if export_resp.status_code != HTTPStatus.OK or isinstance(export_resp.parsed, Error):
                raise RuntimeError(f"Canva export request failed: {export_resp.status_code}")
            export_job_id = export_resp.parsed.job.id

            # 5. Poll export until done
            pdf_url = await _poll_export(client, export_job_id)

            # 6. Download the rendered PDF (raw httpx — no generated endpoint)
            async with httpx.AsyncClient(timeout=60) as http_client:
                pdf_resp = await http_client.get(pdf_url)
                pdf_resp.raise_for_status()
                return pdf_resp.content

    async def _upload_hero_asset(
        self, client: AuthenticatedClient, image_url: str
    ) -> str | None:
        """Upload a hero photo URL as a Canva asset. Returns asset ID or None on failure."""
        try:
            body = CreateUrlAssetUploadJobRequest(name="hero_image", url=image_url)
            resp = await create_url_asset_upload_job.asyncio_detailed(
                client=client, body=body,
            )
            if resp.status_code != HTTPStatus.OK or isinstance(resp.parsed, Error):
                raise RuntimeError(f"Upload request failed: {resp.status_code}")
            job_id = resp.parsed.job.id
            return await _poll_upload(client, job_id)
        except Exception:
            logger.warning("canva.hero_upload_failed url=%s", image_url, exc_info=True)
            return None


async def _poll_autofill(
    client: AuthenticatedClient,
    job_id: str,
    max_attempts: int = 20,
    delay_s: float = 2.0,
) -> str:
    """Poll autofill job until success; return the design ID."""
    for _ in range(max_attempts):
        resp = await get_design_autofill_job.asyncio_detailed(job_id, client=client)
        if isinstance(resp.parsed, Error):
            raise RuntimeError(f"Canva autofill poll error: {resp.parsed}")
        job = resp.parsed.job
        if job.status.value == "success":
            return job.result.design.id
        if job.status.value == "failed":
            raise RuntimeError(f"Canva autofill job failed: {job}")
        await asyncio.sleep(delay_s)
    raise TimeoutError(f"Canva autofill job {job_id} did not complete in time")


async def _poll_export(
    client: AuthenticatedClient,
    export_id: str,
    max_attempts: int = 20,
    delay_s: float = 2.0,
) -> str:
    """Poll export job until success; return the first download URL."""
    for _ in range(max_attempts):
        resp = await get_design_export_job.asyncio_detailed(export_id, client=client)
        if isinstance(resp.parsed, Error):
            raise RuntimeError(f"Canva export poll error: {resp.parsed}")
        job = resp.parsed.job
        if job.status.value == "success":
            return job.urls[0]
        if job.status.value == "failed":
            raise RuntimeError(f"Canva export job failed: {job}")
        await asyncio.sleep(delay_s)
    raise TimeoutError(f"Canva export job {export_id} did not complete in time")


async def _poll_upload(
    client: AuthenticatedClient,
    job_id: str,
    max_attempts: int = 10,
    delay_s: float = 1.5,
) -> str:
    """Poll URL asset upload job until success; return the asset ID."""
    for _ in range(max_attempts):
        resp = await get_url_asset_upload_job.asyncio_detailed(job_id, client=client)
        if isinstance(resp.parsed, Error):
            raise RuntimeError(f"Canva upload poll error: {resp.parsed}")
        job = resp.parsed.job
        if job.status.value == "success":
            return job.asset.id
        if job.status.value == "failed":
            raise RuntimeError(f"Canva upload job failed: {job}")
        await asyncio.sleep(delay_s)
    raise TimeoutError(f"Canva upload job {job_id} did not complete in time")


def _build_autofill_data(
    data: dict, hero_asset_id: str | None = None
) -> CreateDesignAutofillJobRequestData:
    """Convert listing + brand data into Canva autofill request data.

    The CreateDesignAutofillJobRequestData model uses additional_properties
    as a dict of field_name -> DatasetTextValue|DatasetImageValue|DatasetChartValue.
    Since our data shape uses simple dicts matching the Canva API JSON format,
    we build the dict and use from_dict() to let the generated model parse it.
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

    return CreateDesignAutofillJobRequestData.from_dict(fields)


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
