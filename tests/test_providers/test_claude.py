from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from launchlens.providers.base import LLMProvider
from launchlens.providers.claude import ClaudeProvider


def test_claude_provider_is_llm_provider():
    with patch("launchlens.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
        assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
async def test_complete_returns_string():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="A beautiful sun-drenched kitchen.")]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("launchlens.providers.claude.anthropic") as mock_anthropic:
        mock_anthropic.AsyncAnthropic.return_value = mock_client
        provider = ClaudeProvider(api_key="test-key")
        result = await provider.complete(
            prompt="Write a description for this kitchen.",
            context={"listing_id": "abc-123", "beds": 3},
        )

    assert result == "A beautiful sun-drenched kitchen."


@pytest.mark.asyncio
async def test_complete_includes_context_in_prompt():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Lovely home.")]

    mock_client = MagicMock()
    captured_kwargs = {}

    async def capture(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_message

    mock_client.messages.create = capture

    with patch("launchlens.providers.claude.anthropic") as mock_anthropic:
        mock_anthropic.AsyncAnthropic.return_value = mock_client
        provider = ClaudeProvider(api_key="test-key")
        await provider.complete(
            prompt="Write listing copy.",
            context={"beds": 4, "baths": 2},
        )

    messages = captured_kwargs.get("messages", [])
    all_content = " ".join(str(m) for m in messages)
    assert "beds" in all_content or "4" in all_content
