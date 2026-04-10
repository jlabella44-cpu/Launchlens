import base64

import pytest
from pytest_httpx import HTTPXMock

from listingjet.providers.openai_dollhouse import (
    DollhouseRenderError,
    OpenAIDollhouseProvider,
)

_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 512
_FAKE_B64 = base64.b64encode(_FAKE_PNG).decode()


@pytest.mark.asyncio
async def test_generate_downloads_images_and_posts_multipart(httpx_mock: HTTPXMock):
    # Downloads of the two reference images, then the OpenAI edit call.
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/floorplan.jpg",
        content=b"fake-floorplan-bytes",
        headers={"content-type": "image/jpeg"},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/living.jpg",
        content=b"fake-living-bytes",
        headers={"content-type": "image/jpeg"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        json={"data": [{"b64_json": _FAKE_B64}]},
    )

    provider = OpenAIDollhouseProvider(api_key="test-key")
    png = await provider.generate(
        floorplan_url="https://s3.example.com/floorplan.jpg",
        room_photo_urls=["https://s3.example.com/living.jpg"],
    )
    assert png == _FAKE_PNG

    edit_request = httpx_mock.get_request(url="https://api.openai.com/v1/images/edits")
    assert edit_request is not None
    assert edit_request.headers["authorization"] == "Bearer test-key"
    body = edit_request.content.decode("utf-8", errors="replace")
    assert "gpt-image-1.5" in body
    assert "size" in body
    assert "1536x1024" in body
    assert "quality" in body
    assert "medium" in body
    # Multipart field name for multiple images is image[]
    assert 'name="image[]"' in body


@pytest.mark.asyncio
async def test_generate_raises_on_openai_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/floorplan.jpg",
        content=b"bytes",
        headers={"content-type": "image/jpeg"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        status_code=400,
        json={"error": {"message": "content policy violation"}},
    )

    provider = OpenAIDollhouseProvider(api_key="test-key")
    with pytest.raises(DollhouseRenderError) as exc_info:
        await provider.generate(
            floorplan_url="https://s3.example.com/floorplan.jpg",
            room_photo_urls=[],
        )
    assert "400" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_raises_on_missing_api_key():
    provider = OpenAIDollhouseProvider(api_key="")
    with pytest.raises(DollhouseRenderError):
        await provider.generate(
            floorplan_url="https://s3.example.com/floorplan.jpg",
            room_photo_urls=[],
        )


@pytest.mark.asyncio
async def test_generate_caps_at_five_input_images(httpx_mock: HTTPXMock):
    """gpt-image-1.5 preserves the first 5 images; we should not send more."""
    httpx_mock.add_response(
        method="GET",
        url="https://s3.example.com/floorplan.jpg",
        content=b"fp",
        headers={"content-type": "image/jpeg"},
    )
    for i in range(4):
        httpx_mock.add_response(
            method="GET",
            url=f"https://s3.example.com/room{i}.jpg",
            content=b"room",
            headers={"content-type": "image/jpeg"},
        )
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/edits",
        json={"data": [{"b64_json": _FAKE_B64}]},
    )

    provider = OpenAIDollhouseProvider(api_key="test-key")
    # Ask for 6 room photos; only first 4 should be sent (total 5 with floorplan).
    await provider.generate(
        floorplan_url="https://s3.example.com/floorplan.jpg",
        room_photo_urls=[
            f"https://s3.example.com/room{i}.jpg" for i in range(6)
        ],
    )

    # Any 5th/6th room photo should never have been downloaded.
    get_requests = [r for r in httpx_mock.get_requests() if r.method == "GET"]
    urls = {str(r.url) for r in get_requests}
    assert "https://s3.example.com/room4.jpg" not in urls
    assert "https://s3.example.com/room5.jpg" not in urls
    assert len(get_requests) == 5  # floorplan + 4 rooms
