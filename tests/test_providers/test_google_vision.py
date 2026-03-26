import pytest
import httpx
from pytest_httpx import HTTPXMock
from launchlens.providers.google_vision import GoogleVisionProvider
from launchlens.providers.base import VisionLabel

FAKE_RESPONSE = {
    "responses": [{
        "labelAnnotations": [
            {"description": "Living room", "score": 0.97, "mid": "/m/01234"},
            {"description": "Interior design", "score": 0.89, "mid": "/m/05678"},
            {"description": "Hardwood", "score": 0.82, "mid": "/m/09abc"},
        ]
    }]
}


@pytest.mark.asyncio
async def test_analyze_returns_vision_labels(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=FAKE_RESPONSE)
    provider = GoogleVisionProvider(api_key="test-key")
    labels = await provider.analyze(image_url="https://s3.example.com/photo.jpg")
    assert len(labels) == 3
    assert all(isinstance(l, VisionLabel) for l in labels)
    assert labels[0].name == "Living room"
    assert labels[0].confidence == pytest.approx(0.97)


@pytest.mark.asyncio
async def test_analyze_maps_category_from_score(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=FAKE_RESPONSE)
    provider = GoogleVisionProvider(api_key="test-key")
    labels = await provider.analyze(image_url="https://s3.example.com/photo.jpg")
    assert all(l.category == "general" for l in labels)


@pytest.mark.asyncio
async def test_analyze_empty_annotations_returns_empty_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"responses": [{}]})
    provider = GoogleVisionProvider(api_key="test-key")
    labels = await provider.analyze(image_url="https://s3.example.com/photo.jpg")
    assert labels == []


@pytest.mark.asyncio
async def test_analyze_raises_on_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=403)
    provider = GoogleVisionProvider(api_key="bad-key")
    with pytest.raises(httpx.HTTPStatusError):
        await provider.analyze(image_url="https://s3.example.com/photo.jpg")
