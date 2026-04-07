
import httpx
import pytest
from pytest_httpx import HTTPXMock

from listingjet.providers.base import VisionLabel
from listingjet.providers.qwen_vision import QwenVisionProvider

FAKE_QWEN_RESPONSE = {
    "choices": [{
        "message": {
            "content": '{"labels": [{"name": "primary exterior", "confidence": 0.95, "category": "shot_type"}, {"name": "golden hour", "confidence": 0.88, "category": "quality"}]}'
        }
    }]
}


@pytest.mark.asyncio
async def test_analyze_returns_vision_labels(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=FAKE_QWEN_RESPONSE)
    provider = QwenVisionProvider(api_key="test-key", base_url="https://test.example.com/v1")
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
        "choices": [{"message": {"content": "not valid json"}}]
    })
    provider = QwenVisionProvider(api_key="test-key", base_url="https://test.example.com/v1")
    with pytest.raises(ValueError, match="Qwen returned unparseable JSON"):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")


@pytest.mark.asyncio
async def test_analyze_raises_on_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=429)
    provider = QwenVisionProvider(api_key="test-key", base_url="https://test.example.com/v1")
    with pytest.raises(httpx.HTTPStatusError):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")


@pytest.mark.asyncio
async def test_analyze_with_prompt_returns_text(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={
        "choices": [{"message": {"content": '{"rooms": [{"name": "Living Room"}]}'}}]
    })
    provider = QwenVisionProvider(api_key="test-key", base_url="https://test.example.com/v1")
    result = await provider.analyze_with_prompt(
        image_url="https://s3.example.com/photo.jpg",
        prompt="Describe this room.",
    )
    assert "Living Room" in result


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    provider = QwenVisionProvider(api_key="test-key", base_url="https://test.example.com/v1", max_concurrent=3)
    assert provider._semaphore._value == 3


@pytest.mark.asyncio
async def test_endpoint_constructed_from_base_url():
    provider = QwenVisionProvider(
        api_key="test-key",
        base_url="https://dashscope-us.aliyuncs.com/compatible-mode/v1",
    )
    assert provider._endpoint == "https://dashscope-us.aliyuncs.com/compatible-mode/v1/chat/completions"


@pytest.mark.asyncio
async def test_trailing_slash_stripped_from_base_url():
    provider = QwenVisionProvider(
        api_key="test-key",
        base_url="https://dashscope-us.aliyuncs.com/compatible-mode/v1/",
    )
    assert provider._endpoint == "https://dashscope-us.aliyuncs.com/compatible-mode/v1/chat/completions"
