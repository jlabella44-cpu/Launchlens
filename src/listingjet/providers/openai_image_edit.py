"""OpenAI image editing provider — object removal and enhancement.

Uses gpt-image-1.5 via /v1/images/edits so the model actually looks at the
input image (unlike DALL-E 3's text-only /v1/images/generations endpoint).
"""
from __future__ import annotations

import logging

from listingjet.config import settings

from ._openai_edits import (
    OpenAIEditError,
    edit_single_image,
    fetch_image_bytes,
)
from .base import ImageEditProvider

logger = logging.getLogger(__name__)


_ENHANCEMENT_PROMPTS = {
    "brighten": (
        "Keep this exact same real estate photo but brighten the scene as if "
        "it was shot during golden-hour natural sunlight. Preserve the room "
        "layout, architecture, furniture, and finishes exactly as shown. "
        "Balanced exposure, warm tones, crisp shadows, no blown highlights."
    ),
    "fix_lighting": (
        "Rebalance the lighting in this real estate photo so exposure is even "
        "across the frame, shadows are softened, and white balance reads "
        "neutral-warm. Preserve the room layout, architecture, furniture, "
        "and finishes exactly as shown. No HDR halos, no blown highlights."
    ),
    "improve_quality": (
        "Upscale and sharpen this real estate photo to magazine quality while "
        "preserving the room layout, architecture, furniture, and finishes "
        "exactly as shown. Natural colors, no filters, no over-processing."
    ),
    "declutter": (
        "Remove personal items, clutter, stray objects, and visual noise from "
        "this real estate photo. Preserve the room layout, architecture, "
        "walls, flooring, and primary furniture exactly as shown. Surfaces "
        "should look clean and styled, not repainted."
    ),
}


class OpenAIImageEditProvider(ImageEditProvider):
    """Image editor using gpt-image-1.5 via /v1/images/edits."""

    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.openai_api_key

    async def remove_object(self, image_url: str, object_description: str) -> bytes:
        """Remove an object from a real estate photo while preserving the rest."""
        prompt = (
            f"Remove the {object_description} from this real estate photo. "
            f"Preserve the room layout, architecture, furniture, lighting, "
            f"and finishes exactly as shown. Fill the area where the "
            f"{object_description} was with a natural continuation of the "
            f"surrounding background — walls, floor, ceiling, or whatever is "
            f"adjacent. Photorealistic, no artifacts, no warping."
        )

        try:
            image_bytes, content_type = await fetch_image_bytes(image_url)
            result = await edit_single_image(
                api_key=self._api_key,
                image_bytes=image_bytes,
                image_content_type=content_type,
                prompt=prompt,
                provider_label="openai_image_edit",
            )
        except OpenAIEditError:
            raise
        logger.info("image_edit.remove object=%s", object_description)
        return result

    async def enhance(self, image_url: str, enhancement: str) -> bytes:
        """Enhance an image — brighten, fix_lighting, improve_quality, declutter."""
        prompt = _ENHANCEMENT_PROMPTS.get(enhancement, _ENHANCEMENT_PROMPTS["improve_quality"])

        try:
            image_bytes, content_type = await fetch_image_bytes(image_url)
            result = await edit_single_image(
                api_key=self._api_key,
                image_bytes=image_bytes,
                image_content_type=content_type,
                prompt=prompt,
                provider_label="openai_image_edit",
            )
        except OpenAIEditError:
            raise
        logger.info("image_edit.enhance type=%s", enhancement)
        return result
