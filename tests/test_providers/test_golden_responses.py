"""Golden-response tests.

These fixtures mirror the shape of real Qwen/Gemma responses. If a provider
ever returns a different structure (missing usage, nested content, etc.),
these tests catch it before it reaches agents.

To refresh fixtures, capture a real response body with real API keys and
copy the JSON into tests/test_providers/fixtures/.
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from listingjet.providers.gemma import GemmaProvider, GemmaVisionProvider
from listingjet.providers.qwen import QwenProvider, QwenVisionProvider

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class _GoldenResponse:
    def __init__(self, body):
        self._body = body
        self.status_code = 200

    def json(self):
        return self._body

    def raise_for_status(self):
        return None


@pytest.mark.asyncio
async def test_qwen_complete_golden():
    body = _load("qwen_chat_listing.json")
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_GoldenResponse(body))), \
         patch("listingjet.providers.qwen.record_token_usage") as rec, \
         patch("listingjet.providers.qwen.record_provider_call"):
        result = await QwenProvider(api_key="k").complete("write listing", {"beds": 3})
    assert "Craftsman" in result
    rec.assert_called_once_with("qwen", 142, 38)


@pytest.mark.asyncio
async def test_qwen_vision_golden():
    body = _load("qwen_vision_labels.json")
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_GoldenResponse(body))), \
         patch("listingjet.providers.qwen.record_token_usage") as rec, \
         patch("listingjet.providers.qwen.record_provider_call"):
        labels = await QwenVisionProvider(api_key="k").analyze("http://img")
    assert len(labels) == 4
    names = [label.name for label in labels]
    assert "kitchen" in names
    assert "granite countertops" in names
    categories = {label.category for label in labels}
    assert categories == {"room", "feature", "shot_type", "quality"}
    rec.assert_called_once_with("qwen_vision", 620, 72)


@pytest.mark.asyncio
async def test_gemma_complete_golden():
    body = _load("gemma_chat_caption.json")
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_GoldenResponse(body))), \
         patch("listingjet.providers.gemma.record_token_usage") as rec, \
         patch("listingjet.providers.gemma.record_provider_call"):
        result = await GemmaProvider(api_key="k").complete("caption", {})
    assert "#JustListed" in result
    rec.assert_called_once_with("gemma", 88, 24)


@pytest.mark.asyncio
async def test_gemma_vision_golden():
    body = _load("gemma_vision_labels.json")
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_GoldenResponse(body))), \
         patch("listingjet.providers.gemma.record_token_usage"), \
         patch("listingjet.providers.gemma.record_provider_call"):
        labels = await GemmaVisionProvider(api_key="k").analyze("http://img")
    assert len(labels) == 2
    assert labels[0].name == "living room"
    assert labels[0].confidence == pytest.approx(0.96)
