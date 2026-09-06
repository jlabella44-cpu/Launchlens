"""OpenAI gpt-image-1.5 dollhouse render provider.

Thin wrapper around OpenAIImagesClient. Transforms a 2D floorplan plus a
handful of room reference photos into a photorealistic isometric 3D
dollhouse PNG via the Image API edits endpoint.
"""
from __future__ import annotations

from typing import Iterable

from listingjet.config import settings

from .openai_images import DOLLHOUSE_PROMPT, OpenAIEditError, OpenAIImagesClient

# DollhouseRenderError used to be its own class; it's now an alias for the
# shared OpenAIEditError so all OpenAI image failures raise/are caught the
# same way, while existing callers/tests that import DollhouseRenderError
# keep working unchanged.
DollhouseRenderError = OpenAIEditError

__all__ = ["DOLLHOUSE_PROMPT", "DollhouseRenderError", "OpenAIDollhouseProvider"]


class OpenAIDollhouseProvider:
    """Image-to-image dollhouse render via OpenAI gpt-image-1.5."""

    provider_name = "openai_dollhouse"

    def __init__(self, api_key: str | None = None):
        self._client = OpenAIImagesClient(api_key or settings.openai_api_key)

    async def generate(
        self,
        floorplan_url: str,
        room_photo_urls: Iterable[str],
        prompt: str | None = None,
    ) -> bytes:
        """Return a PNG of the rendered dollhouse from HTTP-fetchable URLs."""
        return await self._client.render_dollhouse(floorplan_url, room_photo_urls, prompt)

    async def generate_from_bytes(
        self,
        images: list[tuple[str, bytes, str]],
        prompt: str | None = None,
    ) -> bytes:
        """Return a PNG from an in-memory list of (filename, bytes, content_type)."""
        return await self._client.render_dollhouse_from_bytes(images, prompt)
