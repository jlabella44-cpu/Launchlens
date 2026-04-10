"""OpenAI virtual staging provider.

Uses gpt-image-1.5 via /v1/images/edits so the model actually looks at the
empty room photo (unlike DALL-E 3's text-only generations endpoint). Returns
raw PNG bytes of the staged version.
"""
from __future__ import annotations

import logging

from listingjet.config import settings

from ._openai_edits import (
    OpenAIEditError,
    edit_single_image,
    fetch_image_bytes,
)
from .base import VirtualStagingProvider

logger = logging.getLogger(__name__)

_STAGING_STYLE_DESCRIPTIONS = {
    "modern": "modern furniture with clean lines, neutral tones, and natural light",
    "contemporary": "contemporary furniture with warm wood accents, statement lighting, and curated art",
    "minimalist": "minimalist furniture only, white walls, simple lines, and open space",
    "coastal": "light wood furniture, blue accents, woven textures, and coastal-inspired decor",
    "traditional": "traditional furniture with rich wood tones, elegant fabrics, and warm lighting",
    "luxury": "high-end designer furniture, marble accents, crystal lighting, and premium finishes",
}


def _build_prompt(room_type: str, style: str) -> str:
    room_display = room_type.replace("_", " ")
    style_desc = _STAGING_STYLE_DESCRIPTIONS.get(
        style, _STAGING_STYLE_DESCRIPTIONS["modern"]
    )
    return (
        f"Stage this empty {room_display} photo with {style_desc}. "
        f"Preserve the exact room layout, walls, floors, ceiling, windows, "
        f"doors, and architectural details shown in the photo. Only add the "
        f"furniture and decor — do not change the room itself. Photorealistic "
        f"real estate photography, natural lighting consistent with the "
        f"original photo, no warping or architectural modifications."
    )


class OpenAIVirtualStagingProvider(VirtualStagingProvider):
    """Stage empty rooms using gpt-image-1.5 via /v1/images/edits."""

    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.openai_api_key

    async def stage_image(
        self,
        image_url: str,
        room_type: str,
        style: str = "modern",
    ) -> bytes:
        prompt = _build_prompt(room_type, style)
        try:
            image_bytes, content_type = await fetch_image_bytes(image_url)
            result = await edit_single_image(
                api_key=self._api_key,
                image_bytes=image_bytes,
                image_content_type=content_type,
                prompt=prompt,
                provider_label="openai_staging",
            )
        except OpenAIEditError:
            raise
        logger.info("openai_staging.staged room=%s style=%s", room_type, style)
        return result
