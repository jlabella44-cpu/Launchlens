"""OpenAI virtual staging provider — thin wrapper around OpenAIImagesClient.

Uses gpt-image-1.5 via /v1/images/edits so the model actually looks at the
empty room photo (unlike DALL-E 3's text-only generations endpoint). Returns
raw PNG bytes of the staged version.
"""
from __future__ import annotations

from listingjet.config import settings

from .base import VirtualStagingProvider
from .openai_images import OpenAIEditError, OpenAIImagesClient

__all__ = ["OpenAIEditError", "OpenAIVirtualStagingProvider"]


class OpenAIVirtualStagingProvider(VirtualStagingProvider):
    """Stage empty rooms using gpt-image-1.5 via /v1/images/edits."""

    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        self._client = OpenAIImagesClient(api_key or settings.openai_api_key)

    async def stage_image(
        self,
        image_url: str,
        room_type: str,
        style: str = "modern",
    ) -> bytes:
        return await self._client.stage_room(image_url, room_type, style)
