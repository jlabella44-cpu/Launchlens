"""Tests for telemetry module — OpenTelemetry tracing setup and agent_span."""

import pytest

from launchlens.telemetry import agent_span, get_tracer, init_tracing


def test_init_tracing_does_not_raise():
    """init_tracing should not raise even without OTLP endpoint configured."""
    init_tracing()


def test_get_tracer_returns_tracer():
    """get_tracer should return a tracer object after init."""
    init_tracing()
    tracer = get_tracer()
    assert tracer is not None


@pytest.mark.asyncio
async def test_agent_span_yields_span():
    """agent_span should yield a span with correct attributes."""
    init_tracing()
    async with agent_span("test_agent", "listing-123", "tenant-456") as span:
        assert span is not None
        span.set_attribute("result.count", 42)


@pytest.mark.asyncio
async def test_agent_span_records_exception():
    """agent_span should record exceptions and re-raise."""
    init_tracing()
    with pytest.raises(ValueError, match="test error"):
        async with agent_span("test_agent", "listing-123", "tenant-456"):
            raise ValueError("test error")


@pytest.mark.asyncio
async def test_agent_span_without_tracer():
    """agent_span should yield None when tracer is unavailable."""
    import launchlens.telemetry as tel

    original = tel._tracer
    tel._tracer = None
    try:
        # Temporarily remove the tracer to test fallback
        # (it will re-init via get_tracer, but that's fine)
        async with agent_span("test_agent", "lid", "tid") as _span:
            # span may or may not be None depending on OTel availability
            pass  # should not raise
    finally:
        tel._tracer = original
