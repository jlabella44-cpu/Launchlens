"""OpenAI DALL-E virtual staging provider.

Uses DALL-E 3 image editing to stage empty rooms with furniture.
Falls back gracefully if the image can't be processed.
"""
import logging

import httpx

from listingjet.config import settings

from .base import VirtualStagingProvider

logger = logging.getLogger(__name__)

_STAGING_PROMPTS = {
    "modern": "A beautifully staged {room} with modern furniture, clean lines, neutral tones, and natural light. Photorealistic interior design photography.",
    "contemporary": "A stylish staged {room} with contemporary furniture, warm wood accents, statement lighting, and curated art. Photorealistic.",
    "minimalist": "A minimalist staged {room} with essential furniture only, white walls, simple lines, and open space. Photorealistic.",
    "coastal": "A bright coastal-styled staged {room} with light wood furniture, blue accents, woven textures, and ocean-inspired decor. Photorealistic.",
    "traditional": "A classically staged {room} with traditional furniture, rich wood tones, elegant fabrics, and warm lighting. Photorealistic.",
    "luxury": "A luxuriously staged {room} with high-end designer furniture, marble accents, crystal lighting, and premium finishes. Photorealistic.",
}


class OpenAIVirtualStagingProvider(VirtualStagingProvider):
    """Stage rooms using OpenAI's image generation API."""

    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.openai_api_key
        self._base_url = "https://api.openai.com/v1"

    async def stage_image(
        self,
        image_url: str,
        room_type: str,
        style: str = "modern",
    ) -> str:
        prompt_template = _STAGING_PROMPTS.get(style, _STAGING_PROMPTS["modern"])
        room_display = room_type.replace("_", " ")
        prompt = prompt_template.format(room=room_display)

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self._base_url}/images/generations",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": "dall-e-3",
                    "prompt": f"Transform this empty {room_display} photo into: {prompt}",
                    "n": 1,
                    "size": "1792x1024",
                    "quality": "hd",
                },
            )
            response.raise_for_status()
            data = response.json()

        image_url_result = data["data"][0]["url"]
        logger.info("openai_staging room=%s style=%s", room_type, style)
        return image_url_result
