"""OpenAI image editing provider — object removal and enhancement.

Thin wrapper around OpenAIImagesClient. Uses gpt-image-1.5 via
/v1/images/edits so the model actually looks at the input image (unlike
DALL-E 3's text-only /v1/images/generations endpoint).
"""
from __future__ import annotations

from listingjet.config import settings

from .base import ImageEditProvider
from .openai_images import OpenAIEditError, OpenAIImagesClient

__all__ = ["OpenAIEditError", "OpenAIImageEditProvider"]


class OpenAIImageEditProvider(ImageEditProvider):
    """Image editor using gpt-image-1.5 via /v1/images/edits."""

    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        self._client = OpenAIImagesClient(api_key or settings.openai_api_key)

    async def remove_object(self, image_url: str, object_description: str) -> bytes:
        """Remove an object from a real estate photo while preserving the rest."""
        return await self._client.remove_object(image_url, object_description)

    async def enhance(self, image_url: str, enhancement: str) -> bytes:
        """Enhance an image — brighten, fix_lighting, improve_quality, declutter."""
        return await self._client.enhance(image_url, enhancement)
