"""
Pipeline-level metrics — tracks agent step durations, failures, provider calls, and costs.

Metrics are logged via the standard logger (no external metrics backend).
"""

import logging
import time

from listingjet.config.ai_rates import IMAGE_CALL_RATES, LEGACY_CALL_RATES, TOKEN_RATES

logger = logging.getLogger(__name__)

# Track model IDs we've warned about (to warn once per unknown id)
_warned_unknown_model_ids: set[str] = set()

# Estimated cost per provider call in USD (flat per-call heuristic)
# Legacy mapping for old provider labels; these are flat per-call rates
_LEGACY_PROVIDER_COSTS: dict[str, float] = {
    "claude": 0.05,
    "openai_gpt4v": 0.03,
}

# New mapping keyed by model id (images and legacy video)
PROVIDER_COSTS: dict[str, float] = {**IMAGE_CALL_RATES, **LEGACY_CALL_RATES}


def emit_metric(
    name: str,
    value: float,
    unit: str = "Count",
    dimensions: dict[str, str] | None = None,
) -> None:
    """Log a metric line. Replaces the old CloudWatch emitter — metrics are
    now just structured log lines for external log aggregation."""
    logger.info("metric name=%s value=%s unit=%s dims=%s", name, value, unit, dimensions or {})


# Per-1M-token cost in USD: (input_rate, output_rate)
TOKEN_COSTS: dict[str, tuple[float, float]] = TOKEN_RATES


def track_step_duration(agent_name: str, duration_ms: float) -> None:
    """Record how long an agent step took."""
    emit_metric(
        "AgentStepDuration",
        duration_ms,
        unit="Milliseconds",
        dimensions={"agent": agent_name},
    )


def record_step_failure(agent_name: str) -> None:
    """Increment the failure counter for an agent step."""
    emit_metric(
        "AgentStepFailure",
        1,
        unit="Count",
        dimensions={"agent": agent_name},
    )


def record_provider_call(provider_name: str, success: bool) -> None:
    """Record a provider API call (success or failure)."""
    emit_metric(
        "ProviderCallCount",
        1,
        unit="Count",
        dimensions={"provider": provider_name, "success": str(success)},
    )


def record_token_usage(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    agent_name: str | None = None,
) -> None:
    """Record token counts and compute estimated cost from TOKEN_RATES.

    model_id is the model identifier (e.g. "claude-haiku-4-5", "gpt-image-1.5").
    If unknown, logs a warning once per id and records metrics with cost 0.
    """
    rates = TOKEN_RATES.get(model_id)
    if rates is None:
        if model_id not in _warned_unknown_model_ids:
            logger.warning("Unknown model_id in record_token_usage: %s", model_id)
            _warned_unknown_model_ids.add(model_id)
        cost = 0.0
    else:
        in_rate, out_rate = rates
        cost = (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000

    dims = {"model": model_id}
    if agent_name:
        dims["agent"] = agent_name
    emit_metric("TokensInput", input_tokens, unit="Count", dimensions=dims)
    emit_metric("TokensOutput", output_tokens, unit="Count", dimensions=dims)
    emit_metric("EstimatedCost", cost, unit="None", dimensions=dims)


def record_cost(agent_name: str, provider_name: str, call_count: int = 1) -> None:
    """Record estimated cost for provider usage within an agent.

    provider_name can be either an old provider label (claude, openai_gpt4v, etc.)
    or a model id (gpt-image-1.5, kling, etc.).
    """
    # Try new model id keys first, then fall back to legacy provider labels
    cost_per_call = PROVIDER_COSTS.get(provider_name) or _LEGACY_PROVIDER_COSTS.get(provider_name, 0)
    total = cost_per_call * call_count
    if total > 0:
        emit_metric(
            "EstimatedCost",
            total,
            unit="None",
            dimensions={"agent": agent_name, "provider": provider_name},
        )


def record_review_turnaround(duration_seconds: float) -> None:
    """Record time between AWAITING_REVIEW and approval."""
    emit_metric(
        "ReviewTurnaround",
        duration_seconds,
        unit="Seconds",
        dimensions={},
    )


class StepTimer:
    """Context manager that tracks step duration and records failure on exception."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._start: float = 0

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.monotonic() - self._start) * 1000
        track_step_duration(self.agent_name, duration_ms)
        if exc_type is not None:
            record_step_failure(self.agent_name)
        return False
