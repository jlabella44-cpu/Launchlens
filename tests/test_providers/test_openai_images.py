"""Tests for the consolidated OpenAI images client.

OpenAIImagesClient is the single place that talks to /v1/images/edits via
raw httpx (no `openai` SDK dependency). OpenAIVirtualStagingProvider,
OpenAIImageEditProvider, and OpenAIDollhouseProvider are thin wrappers
around it (see the openai edits and openai dollhouse provider test modules).
"""
import base64

import pytest
from pytest_httpx import HTTPXMock

from listingjet.providers.openai_images import OpenAIEditError, OpenAIImagesClient

_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 256
_FAKE_B64 = base64.b64encode(_FAKE_PNG).decode()


@pytest.mark.asyncio
async def test_edit_posts_multipart_with_input_image(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        json={"data": [{"b64_json": _FAKE_B64}]},
    )

    client = OpenAIImagesClient(api_key="test-key")
    result = await client.edit(
        image_bytes=b"fake-input-image-bytes",
        content_type="image/jpeg",
        prompt="make it look nice",
        label="test_label",
    )
    assert result == _FAKE_PNG

    req = httpx_mock.get_request(url="https://api.openai.com/v1/images/edits")
    assert req is not None
    assert req.headers["authorization"] == "Bearer test-key"
    body = req.content.decode("utf-8", errors="replace")
    assert 'name="image[]"' in body
    assert 'name="prompt"' in body
    assert "make it look nice" in body
    assert "gpt-image-1.5" in body
    assert "fake-input-image-bytes" in body


@pytest.mark.asyncio
async def test_edit_raises_openai_edit_error_on_400(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        status_code=400,
        json={"error": {"message": "content policy violation"}},
    )

    client = OpenAIImagesClient(api_key="test-key")
    with pytest.raises(OpenAIEditError) as exc_info:
        await client.edit(
            image_bytes=b"bytes",
            content_type="image/png",
            prompt="x",
            label="test_label",
        )
    assert "400" in str(exc_info.value)


@pytest.mark.asyncio
async def test_edit_raises_on_missing_api_key():
    client = OpenAIImagesClient(api_key="")
    with pytest.raises(OpenAIEditError):
        await client.edit(
            image_bytes=b"bytes",
            content_type="image/png",
            prompt="x",
            label="test_label",
        )


@pytest.mark.asyncio
async def test_edit_raises_on_empty_bytes():
    client = OpenAIImagesClient(api_key="test-key")
    with pytest.raises(OpenAIEditError):
        await client.edit(
            image_bytes=b"",
            content_type="image/png",
            prompt="x",
            label="test_label",
        )


@pytest.mark.asyncio
async def test_fetch_image_bytes_returns_content_and_type(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/photo.jpg",
        content=b"actual-jpeg-bytes",
        headers={"content-type": "image/jpeg; charset=binary"},
    )
    client = OpenAIImagesClient(api_key="test-key")
    data, ctype = await client.fetch_image_bytes("https://s3.example.com/photo.jpg")
    assert data == b"actual-jpeg-bytes"
    assert ctype == "image/jpeg"


@pytest.mark.asyncio
async def test_edit_from_url_downloads_then_edits(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/photo.jpg",
        content=b"downloaded-bytes",
        headers={"content-type": "image/jpeg"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        json={"data": [{"b64_json": _FAKE_B64}]},
    )
    client = OpenAIImagesClient(api_key="test-key")
    result = await client.edit_from_url(
        "https://s3.example.com/photo.jpg", "a prompt", label="test_label"
    )
    assert result == _FAKE_PNG
    edit_req = httpx_mock.get_request(url="https://api.openai.com/v1/images/edits")
    body = edit_req.content.decode("utf-8", errors="replace")
    assert "downloaded-bytes" in body
