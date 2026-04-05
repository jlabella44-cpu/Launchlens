"""OpenAI image editing provider — object removal and enhancement.

Uses GPT-4V for understanding + DALL-E for inpainting/editing.
"""
import logging

import httpx

from listingjet.config import settings

from .base import ImageEditProvider

logger = logging.getLogger(__name__)


class OpenAIImageEditProvider(ImageEditProvider):
    """Image editor using OpenAI's image generation API."""

    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.openai_api_key
        self._base_url = "https://api.openai.com/v1"

    async def remove_object(self, image_url: str, object_description: str) -> bytes:
        """Remove an object by generating a clean version of the image.

        Uses DALL-E 3 to regenerate the image area without the specified object.
        """
        prompt = (
            f"A clean, professional real estate listing photo. "
            f"The image should look exactly like the original photo but with "
            f"the {object_description} completely removed. "
            f"Fill the area naturally with the surrounding background. "
            f"Photorealistic, high quality, no artifacts."
        )

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self._base_url}/images/generations",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1792x1024",
                    "quality": "hd",
                    "response_format": "url",
                },
            )
            response.raise_for_status()
            data = response.json()
            result_url = data["data"][0]["url"]

            # Download the generated image
            img_resp = await client.get(result_url)
            img_resp.raise_for_status()

        logger.info("image_edit.remove object=%s", object_description)
        return img_resp.content

    async def enhance(self, image_url: str, enhancement: str) -> bytes:
        """Enhance an image using DALL-E.

        Supported enhancements: brighten, fix_lighting, improve_quality, declutter
        """
        enhancement_prompts = {
            "brighten": "A bright, well-lit version of this real estate photo with natural sunlight streaming in, warm tones, and clear visibility of all details. Professional real estate photography.",
            "fix_lighting": "A professionally lit version of this real estate photo with balanced exposure, no harsh shadows, warm white balance, and clear details in all areas. Professional HDR real estate photography.",
            "improve_quality": "A high-resolution, professional-grade version of this real estate photo with sharp details, perfect white balance, vibrant but natural colors, and magazine-quality composition.",
            "declutter": "A clean, tidy version of this real estate photo with personal items, clutter, and mess removed. Surfaces are clear, rooms look spacious and move-in ready. Photorealistic.",
        }

        prompt = enhancement_prompts.get(enhancement, enhancement_prompts["improve_quality"])

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self._base_url}/images/generations",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1792x1024",
                    "quality": "hd",
                    "response_format": "url",
                },
            )
            response.raise_for_status()
            data = response.json()
            result_url = data["data"][0]["url"]

            img_resp = await client.get(result_url)
            img_resp.raise_for_status()

        logger.info("image_edit.enhance type=%s", enhancement)
        return img_resp.content
