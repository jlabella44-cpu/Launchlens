"""OpenAI gpt-image-1.5 dollhouse render provider.

Transforms a 2D floorplan plus a handful of room reference photos into a
photorealistic isometric 3D dollhouse PNG via the Image API edits endpoint.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
from typing import Iterable

import httpx

from listingjet.config import settings
from listingjet.services.metrics import record_provider_call, record_token_usage

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openai.com/v1"
_MODEL = "gpt-image-1.5"
_DEFAULT_SIZE = "1536x1024"  # landscape — gives more horizontal real estate for the dollhouse
_DEFAULT_QUALITY = "medium"  # ~$0.05 per 1536x1024 at medium quality
_MAX_INPUT_IMAGES = 5        # gpt-image-1.5 preserves the first 5 with high fidelity
_DOWNLOAD_TIMEOUT = 30.0
_GENERATE_TIMEOUT = 180.0

DOLLHOUSE_PROMPT = """\
Generate a photorealistic isometric 3D dollhouse render of a real estate listing.

Use the first reference image (a 2D architectural floorplan) as the structural
blueprint — the room layout, wall positions, and proportions must match it
exactly. Extrude the walls upward to create visible rooms that can be looked
into from above. The roof should be removed or transparent so the floorplan
structure stays visible.

Use the other reference images as style and furniture references: match the
wall colors, flooring materials, and furniture visible in each photo to the
corresponding room on the floorplan.

Style: warm architectural visualization, soft natural lighting, subtle
shadows, cream background, isometric three-quarter camera angle looking down
from about 30 degrees above the ground plane. No text labels, no annotations,
no people, no cars. The rooms should feel real but stylized — like a
professional dollhouse miniature used in real estate marketing.
"""


class DollhouseRenderError(RuntimeError):
    """Raised when the OpenAI dollhouse render call fails."""


class OpenAIDollhouseProvider:
    """Image-to-image dollhouse render via OpenAI gpt-image-1.5."""

    provider_name = "openai_dollhouse"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _MODEL,
        size: str = _DEFAULT_SIZE,
        quality: str = _DEFAULT_QUALITY,
    ):
        self._api_key = api_key or settings.openai_api_key
        self._model = model
        self._size = size
        self._quality = quality
        self._endpoint = f"{_BASE_URL}/images/edits"

    async def generate(
        self,
        floorplan_url: str,
        room_photo_urls: Iterable[str],
        prompt: str | None = None,
    ) -> bytes:
        """Return a PNG of the rendered dollhouse from HTTP-fetchable URLs."""
        if not self._api_key:
            raise DollhouseRenderError("OPENAI_API_KEY is not configured")

        image_urls = [floorplan_url] + [u for u in room_photo_urls if u][: _MAX_INPUT_IMAGES - 1]
        if not image_urls:
            raise DollhouseRenderError("At least one image URL is required")

        downloaded: list[tuple[str, bytes, str]] = []
        async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT) as client:
            for i, url in enumerate(image_urls):
                resp = await client.get(url)
                resp.raise_for_status()
                content = resp.content
                content_type = resp.headers.get("content-type", "image/png").split(";")[0].strip()
                ext = mimetypes.guess_extension(content_type) or ".png"
                downloaded.append((f"input_{i}{ext}", content, content_type))

        return await self._send_to_openai(downloaded, prompt or DOLLHOUSE_PROMPT)

    async def generate_from_bytes(
        self,
        images: list[tuple[str, bytes, str]],
        prompt: str | None = None,
    ) -> bytes:
        """Return a PNG from an in-memory list of (filename, bytes, content_type).

        The first image is treated as the floorplan (highest fidelity). Used
        by the smoke script and by any caller that already has bytes in hand.
        """
        if not self._api_key:
            raise DollhouseRenderError("OPENAI_API_KEY is not configured")
        if not images:
            raise DollhouseRenderError("At least one image is required")
        return await self._send_to_openai(
            images[:_MAX_INPUT_IMAGES], prompt or DOLLHOUSE_PROMPT
        )

    async def _send_to_openai(
        self,
        images: list[tuple[str, bytes, str]],
        prompt: str,
    ) -> bytes:
        files = [("image[]", (name, data, ctype)) for name, data, ctype in images]
        data = {
            "model": self._model,
            "prompt": prompt,
            "size": self._size,
            "quality": self._quality,
            "n": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=_GENERATE_TIMEOUT) as client:
                resp = await client.post(
                    self._endpoint,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    data=data,
                    files=files,
                )
                resp.raise_for_status()
                body = resp.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            record_provider_call("openai_dollhouse", False)
            raise DollhouseRenderError(
                f"OpenAI images/edits returned {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            record_provider_call("openai_dollhouse", False)
            raise DollhouseRenderError(f"OpenAI images/edits network error: {exc}") from exc

        try:
            b64 = body["data"][0]["b64_json"]
        except (KeyError, IndexError) as exc:
            record_provider_call("openai_dollhouse", False)
            raise DollhouseRenderError(f"Unexpected response shape: {body}") from exc

        usage = body.get("usage") or {}
        if usage:
            input_tokens = int(usage.get("input_tokens", 0))
            output_tokens = int(usage.get("output_tokens", 0))
            if input_tokens or output_tokens:
                record_token_usage("openai_dollhouse", input_tokens, output_tokens)

        record_provider_call("openai_dollhouse", True)
        png_bytes = base64.b64decode(b64)
        logger.info(
            "dollhouse_render.success model=%s size=%s quality=%s bytes=%d inputs=%d",
            self._model, self._size, self._quality, len(png_bytes), len(images),
        )
        return png_bytes
