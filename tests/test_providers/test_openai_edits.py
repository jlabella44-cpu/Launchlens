"""Tests for OpenAIVirtualStagingProvider and OpenAIImageEditProvider.

Both are thin wrappers around OpenAIImagesClient (see test_openai_images.py
for the shared HTTP-call behavior: multipart body, auth header, error
handling). These tests verify the pieces that were previously broken: both
providers used to call /v1/images/generations (text-only) so they never
actually saw the input image. The fix switches them to /v1/images/edits
with gpt-image-1.5 and passes the input image as multipart form data.
"""
import base64

import pytest
from pytest_httpx import HTTPXMock

from listingjet.providers.openai_image_edit import OpenAIImageEditProvider
from listingjet.providers.openai_images import OpenAIEditError
from listingjet.providers.openai_staging import OpenAIVirtualStagingProvider

_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 256
_FAKE_B64 = base64.b64encode(_FAKE_PNG).decode()


# ---------- OpenAIVirtualStagingProvider ----------


@pytest.mark.asyncio
async def test_staging_provider_actually_sends_input_image(httpx_mock: HTTPXMock):
    """Regression test for the previous bug where stage_image called
    /v1/images/generations (text-only) and never touched the source photo.
    """
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/empty_room.jpg",
        content=b"real-empty-room-bytes",
        headers={"content-type": "image/jpeg"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        json={"data": [{"b64_json": _FAKE_B64}]},
    )

    provider = OpenAIVirtualStagingProvider(api_key="test-key")
    result = await provider.stage_image(
        image_url="https://s3.example.com/empty_room.jpg",
        room_type="living_room",
        style="modern",
    )
    assert result == _FAKE_PNG
    assert isinstance(result, bytes)

    # Confirm we hit the EDITS endpoint, not generations
    edit_req = httpx_mock.get_request(url="https://api.openai.com/v1/images/edits")
    assert edit_req is not None
    body = edit_req.content.decode("utf-8", errors="replace")
    assert "real-empty-room-bytes" in body  # input image was actually sent
    assert "living room" in body
    assert "modern" in body.lower() or "clean lines" in body.lower()


@pytest.mark.asyncio
async def test_staging_provider_raises_on_openai_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/empty.jpg",
        content=b"bytes",
        headers={"content-type": "image/jpeg"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        status_code=400,
        json={"error": {"message": "content policy"}},
    )
    provider = OpenAIVirtualStagingProvider(api_key="test-key")
    with pytest.raises(OpenAIEditError):
        await provider.stage_image(
            image_url="https://s3.example.com/empty.jpg",
            room_type="bedroom",
            style="modern",
        )


# ---------- OpenAIImageEditProvider ----------


@pytest.mark.asyncio
async def test_remove_object_actually_sends_input_image(httpx_mock: HTTPXMock):
    """Regression test — remove_object used to hallucinate a fresh image
    from text alone via the DALL-E 3 generations endpoint. Now it must
    pass the real source bytes to /v1/images/edits.
    """
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/photo.jpg",
        content=b"photo-with-yard-sign-bytes",
        headers={"content-type": "image/jpeg"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        json={"data": [{"b64_json": _FAKE_B64}]},
    )

    provider = OpenAIImageEditProvider(api_key="test-key")
    result = await provider.remove_object(
        image_url="https://s3.example.com/photo.jpg",
        object_description="yard sign",
    )
    assert result == _FAKE_PNG
    assert isinstance(result, bytes)

    edit_req = httpx_mock.get_request(url="https://api.openai.com/v1/images/edits")
    assert edit_req is not None
    body = edit_req.content.decode("utf-8", errors="replace")
    assert "photo-with-yard-sign-bytes" in body
    assert "yard sign" in body


@pytest.mark.asyncio
async def test_enhance_actually_sends_input_image(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/dark.jpg",
        content=b"dim-photo-bytes",
        headers={"content-type": "image/jpeg"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        json={"data": [{"b64_json": _FAKE_B64}]},
    )

    provider = OpenAIImageEditProvider(api_key="test-key")
    result = await provider.enhance(
        image_url="https://s3.example.com/dark.jpg",
        enhancement="brighten",
    )
    assert result == _FAKE_PNG

    edit_req = httpx_mock.get_request(url="https://api.openai.com/v1/images/edits")
    assert edit_req is not None
    body = edit_req.content.decode("utf-8", errors="replace")
    assert "dim-photo-bytes" in body
    assert "golden-hour" in body or "brighten" in body.lower()


@pytest.mark.asyncio
async def test_enhance_falls_back_to_improve_quality_prompt(httpx_mock: HTTPXMock):
    """Unknown enhancement name should use the 'improve_quality' prompt."""
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/photo.jpg",
        content=b"bytes",
        headers={"content-type": "image/jpeg"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        json={"data": [{"b64_json": _FAKE_B64}]},
    )
    provider = OpenAIImageEditProvider(api_key="test-key")
    await provider.enhance(
        image_url="https://s3.example.com/photo.jpg",
        enhancement="unknown_mode_xyz",
    )
    req = httpx_mock.get_request(url="https://api.openai.com/v1/images/edits")
    body = req.content.decode("utf-8", errors="replace")
    assert "magazine quality" in body.lower() or "sharpen" in body.lower()
