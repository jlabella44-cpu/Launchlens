import pytest
from unittest.mock import AsyncMock

from launchlens.providers.base import LLMProvider, VisionLabel, VisionProvider
from launchlens.providers.fallback import FallbackLLMProvider, FallbackVisionProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vision_mock(*, healthy: bool = True) -> VisionProvider:
    """Return a mock VisionProvider that either succeeds or raises."""
    mock = AsyncMock(spec=VisionProvider)
    if healthy:
        mock.analyze.return_value = [
            VisionLabel(name="living room", confidence=0.97, category="room"),
        ]
        mock.analyze_with_prompt.return_value = "A bright living room"
    else:
        mock.analyze.side_effect = RuntimeError("provider unavailable")
        mock.analyze_with_prompt.side_effect = RuntimeError("provider unavailable")
    return mock


def _make_llm_mock(*, healthy: bool = True) -> LLMProvider:
    """Return a mock LLMProvider that either succeeds or raises."""
    mock = AsyncMock(spec=LLMProvider)
    if healthy:
        mock.complete.return_value = "Generated listing copy."
    else:
        mock.complete.side_effect = RuntimeError("provider unavailable")
    return mock


# ---------------------------------------------------------------------------
# FallbackVisionProvider tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_vision_uses_primary_when_healthy():
    primary = _make_vision_mock(healthy=True)
    fallback = _make_vision_mock(healthy=True)

    provider = FallbackVisionProvider(primary, fallback)
    result = await provider.analyze("https://example.com/photo.jpg")

    assert len(result) == 1
    assert result[0].name == "living room"
    assert result[0].confidence == 0.97
    assert result[0].category == "room"

    primary.analyze.assert_awaited_once_with("https://example.com/photo.jpg")
    fallback.analyze.assert_not_awaited()


@pytest.mark.asyncio
async def test_fallback_vision_uses_fallback_on_primary_failure():
    primary = _make_vision_mock(healthy=False)
    fallback = _make_vision_mock(healthy=True)

    provider = FallbackVisionProvider(primary, fallback)
    result = await provider.analyze("https://example.com/photo.jpg")

    assert len(result) == 1
    assert result[0].name == "living room"

    primary.analyze.assert_awaited_once()
    fallback.analyze.assert_awaited_once_with("https://example.com/photo.jpg")


@pytest.mark.asyncio
async def test_fallback_vision_raises_when_both_fail():
    primary = _make_vision_mock(healthy=False)
    fallback = _make_vision_mock(healthy=False)

    provider = FallbackVisionProvider(primary, fallback)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await provider.analyze("https://example.com/photo.jpg")


@pytest.mark.asyncio
async def test_fallback_vision_analyze_with_prompt():
    primary = _make_vision_mock(healthy=False)
    fallback = _make_vision_mock(healthy=True)

    provider = FallbackVisionProvider(primary, fallback)
    result = await provider.analyze_with_prompt(
        "https://example.com/photo.jpg", "Describe this room"
    )

    assert result == "A bright living room"

    primary.analyze_with_prompt.assert_awaited_once()
    fallback.analyze_with_prompt.assert_awaited_once_with(
        "https://example.com/photo.jpg", "Describe this room"
    )


# ---------------------------------------------------------------------------
# FallbackLLMProvider tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_llm_uses_primary_when_healthy():
    primary = _make_llm_mock(healthy=True)
    fallback = _make_llm_mock(healthy=True)

    provider = FallbackLLMProvider(primary, fallback)
    result = await provider.complete("Write a listing", {"beds": 3})

    assert result == "Generated listing copy."

    primary.complete.assert_awaited_once_with("Write a listing", {"beds": 3})
    fallback.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_fallback_llm_uses_fallback_on_primary_failure():
    primary = _make_llm_mock(healthy=False)
    fallback = _make_llm_mock(healthy=True)

    provider = FallbackLLMProvider(primary, fallback)
    result = await provider.complete("Write a listing", {"beds": 3})

    assert result == "Generated listing copy."

    primary.complete.assert_awaited_once()
    fallback.complete.assert_awaited_once_with("Write a listing", {"beds": 3})


@pytest.mark.asyncio
async def test_fallback_llm_raises_when_both_fail():
    primary = _make_llm_mock(healthy=False)
    fallback = _make_llm_mock(healthy=False)

    provider = FallbackLLMProvider(primary, fallback)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await provider.complete("Write a listing", {"beds": 3})
