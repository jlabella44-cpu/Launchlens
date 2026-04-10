"""Shared helper for OpenAI image-to-image calls.

Both OpenAIVirtualStagingProvider and OpenAIImageEditProvider delegate to
edit_single_image() so they get real image-conditioned edits (via the
/v1/images/edits endpoint with gpt-image-1.5) instead of the DALL-E 3
text-only generations endpoint.
"""
from __future__ import annotations

import base64
import logging

import httpx

from listingjet.services.metrics import record_provider_call, record_token_usage

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openai.com/v1"
_EDITS_ENDPOINT = f"{_BASE_URL}/images/edits"

DEFAULT_MODEL = "gpt-image-1.5"
DEFAULT_SIZE = "1536x1024"
DEFAULT_QUALITY = "medium"

_DOWNLOAD_TIMEOUT = 30.0
_EDIT_TIMEOUT = 180.0


class OpenAIEditError(RuntimeError):
    """Raised when an OpenAI image edit call fails."""


async def fetch_image_bytes(url: str) -> tuple[bytes, str]:
    """Download bytes from a URL, return (content, content_type)."""
    async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/png").split(";")[0].strip()
        return resp.content, content_type


async def edit_single_image(
    *,
    api_key: str,
    image_bytes: bytes,
    image_content_type: str,
    prompt: str,
    provider_label: str,
    model: str = DEFAULT_MODEL,
    size: str = DEFAULT_SIZE,
    quality: str = DEFAULT_QUALITY,
) -> bytes:
    """Send a single input image + prompt to /v1/images/edits and return PNG bytes.

    provider_label is used for metrics attribution (e.g. "openai_staging",
    "openai_image_edit").
    """
    if not api_key:
        raise OpenAIEditError("OPENAI_API_KEY is not configured")
    if not image_bytes:
        raise OpenAIEditError("image_bytes must be non-empty")

    filename = "input.png" if image_content_type == "image/png" else "input.jpg"
    files = [("image[]", (filename, image_bytes, image_content_type))]
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
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files=files,
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        record_provider_call(provider_label, False)
        raise OpenAIEditError(
            f"OpenAI images/edits returned {exc.response.status_code}: {detail}"
        ) from exc
    except httpx.HTTPError as exc:
        record_provider_call(provider_label, False)
        raise OpenAIEditError(f"OpenAI images/edits network error: {exc}") from exc

    try:
        b64 = body["data"][0]["b64_json"]
    except (KeyError, IndexError) as exc:
        record_provider_call(provider_label, False)
        raise OpenAIEditError(f"Unexpected response shape: {body}") from exc

    usage = body.get("usage") or {}
    if usage:
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        if input_tokens or output_tokens:
            record_token_usage(provider_label, input_tokens, output_tokens)

    record_provider_call(provider_label, True)
    png_bytes = base64.b64decode(b64)
    logger.info(
        "%s.edit_single_image model=%s size=%s quality=%s bytes=%d",
        provider_label, model, size, quality, len(png_bytes),
    )
    return png_bytes
