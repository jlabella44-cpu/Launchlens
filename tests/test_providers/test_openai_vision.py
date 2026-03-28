
import httpx
import pytest
from pytest_httpx import HTTPXMock

from launchlens.providers.base import VisionLabel
from launchlens.providers.openai_vision import OpenAIVisionProvider

FAKE_GPT_RESPONSE = {
    "choices": [{
        "message": {
            "content": '{"labels": [{"name": "primary exterior", "confidence": 0.95, "category": "shot_type"}, {"name": "golden hour", "confidence": 0.88, "category": "quality"}]}'
        }
    }]
}


@pytest.mark.asyncio
async def test_analyze_returns_vision_labels(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=FAKE_GPT_RESPONSE)
    provider = OpenAIVisionProvider(api_key="test-key")
    labels = await provider.analyze(image_url="https://s3.example.com/photo.jpg")
    assert len(labels) == 2
    assert all(isinstance(lbl, VisionLabel) for lbl in labels)
    assert labels[0].name == "primary exterior"
    assert labels[0].category == "shot_type"


@pytest.mark.asyncio
async def test_analyze_raises_on_malformed_json(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={
        "choices": [{"message": {"content": "not valid json"}}]
    })
    provider = OpenAIVisionProvider(api_key="test-key")
    with pytest.raises(ValueError, match="GPT-4V returned unparseable JSON"):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")


@pytest.mark.asyncio
async def test_analyze_raises_on_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=429)
    provider = OpenAIVisionProvider(api_key="test-key")
    with pytest.raises(httpx.HTTPStatusError):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    provider = OpenAIVisionProvider(api_key="test-key", max_concurrent=5)
    assert provider._semaphore._value == 5
