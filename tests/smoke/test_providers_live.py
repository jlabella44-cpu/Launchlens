"""
Live provider smoke tests.

These make REAL network calls to Qwen (DashScope) and Gemma (Gemini API)
with the API keys supplied via env vars. They are NOT part of the default
test run — they are invoked only from the scheduled GitHub Actions
workflow (`.github/workflows/provider-smoke-test.yml`) to catch upstream
breakage early.

Each test skips automatically if the required API key is absent so local
runs don't accidentally burn credits.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_SMOKE", "").lower() not in ("1", "true", "yes"),
    reason="Live smoke tests only run with RUN_LIVE_SMOKE=true",
)


@pytest.mark.asyncio
async def test_qwen_complete_live():
    """Verify a real Qwen chat completion round-trips successfully."""
    if not os.getenv("QWEN_API_KEY"):
        pytest.skip("QWEN_API_KEY not set")
    from listingjet.providers.qwen import QwenProvider

    provider = QwenProvider()
    result = await provider.complete(
        "Write one sentence about a 3-bedroom home.",
        {"beds": 3, "baths": 2},
        temperature=0.2,
    )
    assert isinstance(result, str)
    assert len(result) > 10


@pytest.mark.asyncio
async def test_qwen_vision_live():
    """Verify Qwen vision returns valid label JSON."""
    if not os.getenv("QWEN_API_KEY"):
        pytest.skip("QWEN_API_KEY not set")
    from listingjet.providers.qwen import QwenVisionProvider

    # Public test image (small real-estate stock photo)
    url = "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400"
    provider = QwenVisionProvider()
    labels = await provider.analyze(url)
    assert len(labels) >= 1
    assert all(0.0 <= lab.confidence <= 1.0 for lab in labels)


@pytest.mark.asyncio
async def test_gemma_complete_live():
    """Verify a real Gemma chat completion round-trips successfully."""
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    from listingjet.providers.gemma import GemmaProvider

    provider = GemmaProvider()
    result = await provider.complete(
        "Write one sentence about a 3-bedroom home.",
        {"beds": 3, "baths": 2},
        temperature=0.2,
    )
    assert isinstance(result, str)
    assert len(result) > 10


@pytest.mark.asyncio
async def test_gemma_vision_live():
    """Verify Gemma vision returns valid label JSON."""
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    from listingjet.providers.gemma import GemmaVisionProvider

    url = "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400"
    provider = GemmaVisionProvider()
    labels = await provider.analyze(url)
    assert len(labels) >= 1
    assert all(0.0 <= lab.confidence <= 1.0 for lab in labels)
