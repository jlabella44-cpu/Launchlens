
import httpx
import pytest
from pytest_httpx import HTTPXMock

from listingjet.providers.base import VisionLabel
from listingjet.providers.qwen import QwenVisionProvider

FAKE_QWEN_RESPONSE = {
    "choices": [{
        "message": {
            "content": '{"labels": [{"name": "primary exterior", "confidence": 0.95, "category": "shot_type"}, {"name": "golden hour", "confidence": 0.88, "category": "quality"}]}'
        }
    }],
    "usage": {"prompt_tokens": 100, "completion_tokens": 50},
}


@pytest.mark.asyncio
async def test_analyze_returns_vision_labels(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=FAKE_QWEN_RESPONSE)
    provider = QwenVisionProvider(api_key="test-key")
    labels = await provider.analyze(image_url="https://s3.example.com/photo.jpg")
    assert len(labels) == 2
    assert all(isinstance(lbl, VisionLabel) for lbl in labels)
    assert labels[0].name == "primary exterior"
    assert labels[0].category == "shot_type"
    assert labels[1].name == "golden hour"
    assert labels[1].confidence == 0.88


@pytest.mark.asyncio
async def test_analyze_raises_on_malformed_json(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={
        "choices": [{"message": {"content": "not valid json"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    })
    provider = QwenVisionProvider(api_key="test-key")
    with pytest.raises(ValueError):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")


@pytest.mark.asyncio
async def test_analyze_raises_on_http_error(httpx_mock: HTTPXMock):
    # Provider retries 429s up to 3 times, so provide 3 error responses
    for _ in range(3):
        httpx_mock.add_response(status_code=429)
    provider = QwenVisionProvider(api_key="test-key")
    with pytest.raises(httpx.HTTPStatusError):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")


@pytest.mark.asyncio
async def test_analyze_with_prompt_returns_text(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={
        "choices": [{"message": {"content": '{"rooms": [{"name": "Living Room"}]}'}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    })
    provider = QwenVisionProvider(api_key="test-key")
    result = await provider.analyze_with_prompt(
        image_url="https://s3.example.com/photo.jpg",
        prompt="Describe this room.",
    )
    assert "Living Room" in result


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    provider = QwenVisionProvider(api_key="test-key", max_concurrent=3)
    assert provider._semaphore._value == 3
