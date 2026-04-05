"""Tests for Qwen and Gemma providers — payload shape, usage tracking, retries."""
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from listingjet.providers.gemma import GemmaProvider, GemmaVisionProvider
from listingjet.providers.qwen import QwenProvider, QwenVisionProvider


def _chat_response(content: str = "hello", prompt_tokens: int = 10, completion_tokens: int = 5):
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }


class _FakeResponse:
    def __init__(self, json_body, status_code=200):
        self._json = json_body
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err", request=httpx.Request("POST", "http://x"),
                response=httpx.Response(self.status_code),
            )


@pytest.mark.asyncio
async def test_qwen_complete_records_usage():
    provider = QwenProvider(api_key="k")
    fake = _FakeResponse(_chat_response("nice home"))
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake)) as post, \
         patch("listingjet.providers.qwen.record_token_usage") as rec_tokens, \
         patch("listingjet.providers.qwen.record_provider_call") as rec_call:
        result = await provider.complete("prompt", {"k": "v"}, temperature=0.5)
    assert result == "nice home"
    post.assert_called_once()
    rec_call.assert_called_once_with("qwen", True)
    rec_tokens.assert_called_once_with("qwen", 10, 5)
    # Check payload shape
    _, kwargs = post.call_args
    payload = kwargs["json"]
    assert payload["model"] == "qwen3.6-plus"
    assert payload["temperature"] == 0.5
    assert len(payload["messages"]) == 2


@pytest.mark.asyncio
async def test_qwen_vision_analyze_parses_labels():
    provider = QwenVisionProvider(api_key="k")
    labels_json = '{"labels": [{"name": "kitchen", "confidence": 0.9, "category": "room"}]}'
    fake = _FakeResponse(_chat_response(labels_json, 20, 8))
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake)), \
         patch("listingjet.providers.qwen.record_token_usage"), \
         patch("listingjet.providers.qwen.record_provider_call"):
        labels = await provider.analyze("http://img")
    assert len(labels) == 1
    assert labels[0].name == "kitchen"
    assert labels[0].category == "room"


@pytest.mark.asyncio
async def test_qwen_vision_raises_on_bad_json():
    provider = QwenVisionProvider(api_key="k")
    fake = _FakeResponse(_chat_response("not json"))
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake)), \
         patch("listingjet.providers.qwen.record_token_usage"), \
         patch("listingjet.providers.qwen.record_provider_call"):
        with pytest.raises(ValueError, match="unparseable JSON"):
            await provider.analyze("http://img")


@pytest.mark.asyncio
async def test_gemma_complete_uses_gemini_endpoint():
    provider = GemmaProvider(api_key="k")
    fake = _FakeResponse(_chat_response("cheap copy"))
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake)) as post, \
         patch("listingjet.providers.gemma.record_token_usage"), \
         patch("listingjet.providers.gemma.record_provider_call"):
        result = await provider.complete("prompt", {})
    assert result == "cheap copy"
    args, kwargs = post.call_args
    assert "generativelanguage.googleapis.com" in args[0]
    assert kwargs["json"]["model"] == "gemma-4-31b-it"


@pytest.mark.asyncio
async def test_gemma_vision_analyze_with_prompt_returns_raw():
    provider = GemmaVisionProvider(api_key="k")
    fake = _FakeResponse(_chat_response("raw description"))
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake)), \
         patch("listingjet.providers.gemma.record_token_usage"), \
         patch("listingjet.providers.gemma.record_provider_call"):
        out = await provider.analyze_with_prompt("http://img", "describe")
    assert out == "raw description"


@pytest.mark.asyncio
async def test_qwen_retries_on_500_then_succeeds():
    provider = QwenProvider(api_key="k")
    err = _FakeResponse({}, status_code=503)
    ok = _FakeResponse(_chat_response("finally"))
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=[err, ok])) as post, \
         patch("asyncio.sleep", new=AsyncMock()), \
         patch("listingjet.providers.qwen.record_token_usage"), \
         patch("listingjet.providers.qwen.record_provider_call"):
        result = await provider.complete("p", {})
    assert result == "finally"
    assert post.call_count == 2


@pytest.mark.asyncio
async def test_qwen_does_not_retry_on_400():
    provider = QwenProvider(api_key="k")
    err = _FakeResponse({}, status_code=400)
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=err)) as post, \
         patch("asyncio.sleep", new=AsyncMock()), \
         patch("listingjet.providers.qwen.record_provider_call"):
        with pytest.raises(httpx.HTTPStatusError):
            await provider.complete("p", {})
    assert post.call_count == 1
