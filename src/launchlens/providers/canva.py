# src/launchlens/providers/canva.py
"""Canva Connect API template provider."""
import logging

import httpx

from .base import LLMProvider, TemplateProvider

logger = logging.getLogger(__name__)

_CANVA_API_BASE = "https://api.canva.com/rest/v1"


class CanvaTemplateProvider(TemplateProvider):
    """Renders listing flyers via the Canva Connect API."""

    def __init__(self, api_key: str, llm_provider: LLMProvider | None = None):
        self._api_key = api_key
        self._llm = llm_provider

    async def render(self, template_id: str, data: dict) -> bytes:
        """
        Autofill a Canva design with listing data and export it as a PDF.

        Steps:
        1. POST /autofills — kick off an autofill job for the given brand template.
        2. Poll GET /autofills/{job_id} until status == 'success'.
        3. POST /exports — request a PDF export of the resulting design.
        4. Poll GET /exports/{job_id} until status == 'success', then download.
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(base_url=_CANVA_API_BASE, timeout=60) as client:
            # 1. Start autofill
            autofill_resp = await client.post(
                "/autofills",
                headers=headers,
                json={
                    "brand_template_id": template_id,
                    "data": _build_autofill_data(data),
                },
            )
            autofill_resp.raise_for_status()
            autofill_job = autofill_resp.json()["job"]
            design_id = await _poll_job(client, headers, f"/autofills/{autofill_job['id']}", "design_id")

            # 2. Export as PDF
            export_resp = await client.post(
                "/exports",
                headers=headers,
                json={"design_id": design_id, "format": "pdf"},
            )
            export_resp.raise_for_status()
            export_job = export_resp.json()["job"]
            pdf_url = await _poll_job(client, headers, f"/exports/{export_job['id']}", "url")

            # 3. Download the rendered PDF
            pdf_resp = await client.get(pdf_url)
            pdf_resp.raise_for_status()
            return pdf_resp.content


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


def _build_autofill_data(data: dict) -> list[dict]:
    """Convert listing data dict into Canva autofill field objects."""
    field_map = {
        "address": "property_address",
        "price": "listing_price",
        "bedrooms": "bedrooms",
        "bathrooms": "bathrooms",
        "sqft": "square_footage",
        "description": "property_description",
        "agent_name": "agent_name",
        "agent_phone": "agent_phone",
        "agent_email": "agent_email",
        "photo_url": "hero_image_url",
    }
    fields = []
    for data_key, canva_field in field_map.items():
        if data_key in data:
            fields.append({"name": canva_field, "value": {"type": "text", "text": str(data[data_key])}})
    return fields
