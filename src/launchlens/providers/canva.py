"""CanvaProvider — two-step design rendering via the Canva Connect API.

Step 1: Claude generates a design-spec JSON (layout, colors, text blocks).
Step 2: Canva renders the spec via their Design API and returns a public URL.

This is used by the BrandAgent for flyer generation when `template_provider`
is set to "canva".
"""
import json

import httpx

from launchlens.providers.base import LLMProvider

_CANVA_API_BASE = "https://api.canva.com/rest/v1"

_DESIGN_PROMPT_TEMPLATE = """\
You are a real estate marketing designer. Create a Canva design spec for a property flyer.

Property details:
{details}

Return ONLY valid JSON with this structure:
{{
  "template_id": "listing-flyer-v1",
  "background_color": "#FFFFFF",
  "text_blocks": [
    {{"id": "headline", "text": "...", "font_size": 36, "color": "#111111"}},
    {{"id": "address", "text": "...", "font_size": 18, "color": "#555555"}},
    {{"id": "details", "text": "...", "font_size": 14, "color": "#555555"}}
  ],
  "image_url": "{hero_image_url}"
}}
"""


class CanvaProvider:
    """Renders listing flyers by combining Claude's design JSON with Canva's render API."""

    def __init__(self, api_token: str, llm_provider: LLMProvider | None = None):
        self._token = api_token
        self._llm = llm_provider

    async def render_flyer(
        self,
        listing_details: dict,
        hero_image_url: str = "",
        brand_color: str = "#2563EB",
    ) -> str:
        """Generate and render a listing flyer. Returns the Canva export URL."""
        design_json = await self._generate_design_spec(listing_details, hero_image_url, brand_color)
        export_url = await self._render_with_canva(design_json)
        return export_url

    async def _generate_design_spec(
        self, listing_details: dict, hero_image_url: str, brand_color: str
    ) -> dict:
        """Step 1: Ask Claude to produce a design spec JSON."""
        if self._llm is None:
            raise RuntimeError("LLM provider required for design spec generation")

        details_text = json.dumps(listing_details, indent=2)
        prompt = _DESIGN_PROMPT_TEMPLATE.format(
            details=details_text,
            hero_image_url=hero_image_url,
        )
        raw = await self._llm.complete(prompt=prompt, context={"brand_color": brand_color})

        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        return json.loads(raw)

    async def _render_with_canva(self, design_spec: dict) -> str:
        """Step 2: Send design spec to Canva and return the export URL."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{_CANVA_API_BASE}/designs",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                json={"design": design_spec},
            )
            response.raise_for_status()
            design_id = response.json()["design"]["id"]

            # Export the design as PDF
            export_response = await client.post(
                f"{_CANVA_API_BASE}/exports",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                json={"design_id": design_id, "format": "pdf"},
            )
            export_response.raise_for_status()
            return export_response.json()["export"]["url"]
