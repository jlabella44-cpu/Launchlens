from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from listingjet.providers.base import LLMProvider
from listingjet.providers.claude import ClaudeClient, ClaudeProvider, ProviderOutputError


class Out(BaseModel):
    room: str
    score: int


def _resp(parsed=None, text="hello", stop_reason="end_turn", in_tok=10, out_tok=5):
    return SimpleNamespace(
        parsed_output=parsed, stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


def test_claude_provider_is_llm_provider():
    provider = ClaudeProvider(api_key="test-key")
    assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
async def test_complete_json_uses_parse_and_records_usage():
    c = ClaudeClient(api_key="k")
    c._client.messages.parse = AsyncMock(return_value=_resp(parsed=Out(room="kitchen", score=80)))
    with patch("listingjet.providers.claude.record_token_usage") as rec, \
         patch("listingjet.providers.claude.settings") as s:
        s.claude_quality_model = "claude-sonnet-5"
        out = await c.complete_json("classify", Out, agent="test")
    assert out == Out(room="kitchen", score=80)
    kw = c._client.messages.parse.await_args.kwargs
    assert kw["model"] == "claude-sonnet-5" and kw["output_format"] is Out
    assert "temperature" not in kw and "thinking" not in kw
    rec.assert_called_once_with("claude-sonnet-5", 10, 5, "test")


@pytest.mark.asyncio
async def test_analyze_images_puts_image_blocks_before_text():
    c = ClaudeClient(api_key="k")
    c._client.messages.parse = AsyncMock(return_value=_resp(parsed=Out(room="bath", score=1)))
    with patch("listingjet.providers.claude.settings") as s:
        s.claude_fast_model = "claude-haiku-4-5"
        await c.analyze_images(["https://x/1.jpg", "https://x/2.jpg"], "which room", Out, model="claude-haiku-4-5")
    content = c._client.messages.parse.await_args.kwargs["messages"][0]["content"]
    assert [b["type"] for b in content] == ["image", "image", "text"]
    assert content[0]["source"] == {"type": "url", "url": "https://x/1.jpg"}


@pytest.mark.asyncio
async def test_none_parsed_output_raises_provider_output_error():
    c = ClaudeClient(api_key="k")
    c._client.messages.parse = AsyncMock(return_value=_resp(parsed=None, stop_reason="refusal"))
    with patch("listingjet.providers.claude.record_provider_call") as rec, \
         patch("listingjet.providers.claude.settings") as s:
        s.claude_quality_model = "claude-sonnet-5"
        with pytest.raises(ProviderOutputError):
            await c.complete_json("x", Out)
    rec.assert_called_once_with("claude", False)


@pytest.mark.asyncio
async def test_shim_ignores_temperature_and_appends_context():
    p = ClaudeProvider(api_key="k")
    p._client.complete_text = AsyncMock(return_value="copy")
    out = await p.complete("write", {"beds": 3}, temperature=0.9, system_prompt="sys")
    assert out == "copy"
    kw = p._client.complete_text.await_args
    assert '"beds": 3' in kw.args[0] and kw.kwargs["system"] == "sys"


@pytest.mark.asyncio
async def test_complete_text_uses_messages_create_and_records_usage():
    c = ClaudeClient(api_key="k")
    c._client.messages.create = AsyncMock(return_value=_resp(text="hello there"))
    with patch("listingjet.providers.claude.record_token_usage") as rec, \
         patch("listingjet.providers.claude.settings") as s:
        s.claude_quality_model = "claude-sonnet-5"
        out = await c.complete_text("write copy", agent="content")
    assert out == "hello there"
    kw = c._client.messages.create.await_args.kwargs
    assert kw["model"] == "claude-sonnet-5"
    assert "temperature" not in kw and "top_p" not in kw and "thinking" not in kw
    rec.assert_called_once_with("claude-sonnet-5", 10, 5, "content")
