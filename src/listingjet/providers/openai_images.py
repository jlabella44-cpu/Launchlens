"""Single OpenAI images client — every gpt-image-1.5 call goes through here.

Staging, object removal, enhancement, and dollhouse rendering all use the
/v1/images/edits endpoint (not the text-only /v1/images/generations
endpoint) so the model actually looks at the input image(s). Uses raw
httpx — no `openai` SDK dependency.

OpenAIVirtualStagingProvider, OpenAIImageEditProvider, and
OpenAIDollhouseProvider (in their own modules) are thin wrappers around
OpenAIImagesClient that exist only so factory.py, agents/dollhouse_render.py,
and api/image_edit.py keep their existing constructor/method surface.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
from typing import Iterable

import httpx

from listingjet.config import settings
from listingjet.services.metrics import record_image_call, record_provider_call

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openai.com/v1"
_EDITS_ENDPOINT = f"{_BASE_URL}/images/edits"

DEFAULT_MODEL = "gpt-image-1.5"
DEFAULT_SIZE = "1536x1024"
DEFAULT_QUALITY = "medium"

_DOWNLOAD_TIMEOUT = 30.0
_EDIT_TIMEOUT = 180.0
_MAX_DOLLHOUSE_IMAGES = 5  # gpt-image-1.5 preserves the first 5 with high fidelity

_STAGING_STYLE_DESCRIPTIONS = {
    "modern": "modern furniture with clean lines, neutral tones, and natural light",
    "contemporary": "contemporary furniture with warm wood accents, statement lighting, and curated art",
    "minimalist": "minimalist furniture only, white walls, simple lines, and open space",
    "coastal": "light wood furniture, blue accents, woven textures, and coastal-inspired decor",
    "traditional": "traditional furniture with rich wood tones, elegant fabrics, and warm lighting",
    "luxury": "high-end designer furniture, marble accents, crystal lighting, and premium finishes",
}

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


class OpenAIEditError(RuntimeError):
    """Raised when an OpenAI image edit call fails."""


def _build_staging_prompt(room_type: str, style: str) -> str:
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


def _build_remove_object_prompt(object_description: str) -> str:
    return (
        f"Remove the {object_description} from this real estate photo. "
        f"Preserve the room layout, architecture, furniture, lighting, "
        f"and finishes exactly as shown. Fill the area where the "
        f"{object_description} was with a natural continuation of the "
        f"surrounding background — walls, floor, ceiling, or whatever is "
        f"adjacent. Photorealistic, no artifacts, no warping."
    )


class OpenAIImagesClient:
    """All OpenAI image generation/editing calls (gpt-image-1.5 via /v1/images/edits)."""

    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.openai_api_key

    async def fetch_image_bytes(self, url: str) -> tuple[bytes, str]:
        """Download bytes from a URL, return (content, content_type)."""
        async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/png").split(";")[0].strip()
            return resp.content, content_type

    async def edit(
        self,
        image_bytes: bytes,
        content_type: str,
        prompt: str,
        *,
        label: str,
        model: str = DEFAULT_MODEL,
        size: str = DEFAULT_SIZE,
        quality: str = DEFAULT_QUALITY,
    ) -> bytes:
        """Send a single input image + prompt to /v1/images/edits, return PNG bytes.

        label is used for metrics attribution (e.g. "openai_staging",
        "openai_image_edit").
        """
        if not self._api_key:
            raise OpenAIEditError("OPENAI_API_KEY is not configured")
        if not image_bytes:
            raise OpenAIEditError("image_bytes must be non-empty")

        filename = "input.png" if content_type == "image/png" else "input.jpg"
        images = [(filename, image_bytes, content_type)]
        return await self._send(
            images, prompt, label=label, model=model, size=size, quality=quality
        )

    async def edit_from_url(self, url: str, prompt: str, *, label: str) -> bytes:
        """Download the image at url, then edit() it."""
        image_bytes, content_type = await self.fetch_image_bytes(url)
        return await self.edit(image_bytes, content_type, prompt, label=label)

    async def stage_room(self, image_url: str, room_type: str, style: str = "modern") -> bytes:
        prompt = _build_staging_prompt(room_type, style)
        result = await self.edit_from_url(image_url, prompt, label="openai_staging")
        logger.info("openai_staging.staged room=%s style=%s", room_type, style)
        return result

    async def remove_object(self, image_url: str, description: str) -> bytes:
        prompt = _build_remove_object_prompt(description)
        result = await self.edit_from_url(image_url, prompt, label="openai_image_edit")
        logger.info("image_edit.remove object=%s", description)
        return result

    async def enhance(self, image_url: str, enhancement: str) -> bytes:
        prompt = _ENHANCEMENT_PROMPTS.get(enhancement, _ENHANCEMENT_PROMPTS["improve_quality"])
        result = await self.edit_from_url(image_url, prompt, label="openai_image_edit")
        logger.info("image_edit.enhance type=%s", enhancement)
        return result

    async def render_dollhouse(
        self,
        floorplan_url: str,
        room_photo_urls: Iterable[str],
        prompt: str | None = None,
    ) -> bytes:
        """Return a PNG of the rendered dollhouse from HTTP-fetchable URLs."""
        if not self._api_key:
            raise OpenAIEditError("OPENAI_API_KEY is not configured")

        image_urls = [floorplan_url] + [
            u for u in room_photo_urls if u
        ][: _MAX_DOLLHOUSE_IMAGES - 1]
        if not image_urls:
            raise OpenAIEditError("At least one image URL is required")

        downloaded: list[tuple[str, bytes, str]] = []
        async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT) as client:
            for i, url in enumerate(image_urls):
                resp = await client.get(url)
                resp.raise_for_status()
                content = resp.content
                content_type = resp.headers.get("content-type", "image/png").split(";")[0].strip()
                ext = mimetypes.guess_extension(content_type) or ".png"
                downloaded.append((f"input_{i}{ext}", content, content_type))

        return await self._send(
            downloaded, prompt or DOLLHOUSE_PROMPT, label="openai_dollhouse"
        )

    async def render_dollhouse_from_bytes(
        self,
        images: list[tuple[str, bytes, str]],
        prompt: str | None = None,
    ) -> bytes:
        """Return a PNG from an in-memory list of (filename, bytes, content_type).

        The first image is treated as the floorplan (highest fidelity). Used
        by the smoke script and by any caller that already has bytes in hand.
        """
        if not self._api_key:
            raise OpenAIEditError("OPENAI_API_KEY is not configured")
        if not images:
            raise OpenAIEditError("At least one image is required")
        return await self._send(
            images[:_MAX_DOLLHOUSE_IMAGES], prompt or DOLLHOUSE_PROMPT, label="openai_dollhouse"
        )

    async def _send(
        self,
        images: list[tuple[str, bytes, str]],
        prompt: str,
        *,
        label: str,
        model: str = DEFAULT_MODEL,
        size: str = DEFAULT_SIZE,
        quality: str = DEFAULT_QUALITY,
    ) -> bytes:
        files = [("image[]", image) for image in images]
        data = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=_EDIT_TIMEOUT) as client:
                resp = await client.post(
                    _EDITS_ENDPOINT,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    data=data,
                    files=files,
                )
                resp.raise_for_status()
                body = resp.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            record_provider_call(label, False)
            raise OpenAIEditError(
                f"OpenAI images/edits returned {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            record_provider_call(label, False)
            raise OpenAIEditError(f"OpenAI images/edits network error: {exc}") from exc

        try:
            b64 = body["data"][0]["b64_json"]
        except (KeyError, IndexError) as exc:
            record_provider_call(label, False)
            raise OpenAIEditError(f"Unexpected response shape: {body}") from exc

        record_provider_call(label, True)
        record_image_call(model, label)
        png_bytes = base64.b64decode(b64)
        logger.info(
            "%s.edit model=%s size=%s quality=%s bytes=%d",
            label, model, size, quality, len(png_bytes),
        )
        return png_bytes
