"""
Pipeline-level metrics — tracks agent step durations, failures, provider calls, and costs.

All functions are no-ops in development to avoid CloudWatch calls during local work.
"""

import logging
import time

from listingjet.monitoring.metrics import emit_metric

logger = logging.getLogger(__name__)

# Estimated cost per provider call in USD (flat per-call heuristic)
PROVIDER_COSTS: dict[str, float] = {
    "google_vision": 0.02,
    "claude": 0.05,
    "openai_gpt4v": 0.03,
    "kling": 0.50,
    "qwen": 0.01,
    "qwen_vision": 0.005,
    "gemma": 0.003,
    "gemma_vision": 0.003,
}

# Per-1M-token cost in USD: (input_rate, output_rate)
TOKEN_COSTS: dict[str, tuple[float, float]] = {
    "claude": (3.00, 15.00),
    "qwen": (0.26, 1.56),      # estimated from Qwen3.5-Plus rates
    "qwen_vision": (0.26, 1.56),
    "gemma": (0.14, 0.40),     # Gemma 4 31B via Gemini API
    "gemma_vision": (0.14, 0.40),
    "openai_gpt4v": (2.50, 10.00),
}


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
    provider_name: str,
    input_tokens: int,
    output_tokens: int,
    agent_name: str | None = None,
) -> None:
    """Record token counts and compute estimated cost from TOKEN_COSTS."""
    rates = TOKEN_COSTS.get(provider_name)
    if rates is None:
        return
    in_rate, out_rate = rates
    cost = (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
    dims = {"provider": provider_name}
    if agent_name:
        dims["agent"] = agent_name
    emit_metric("TokensInput", input_tokens, unit="Count", dimensions=dims)
    emit_metric("TokensOutput", output_tokens, unit="Count", dimensions=dims)
    emit_metric("EstimatedCost", cost, unit="None", dimensions=dims)


def record_cost(agent_name: str, provider_name: str, call_count: int = 1) -> None:
    """Record estimated cost for provider usage within an agent."""
    cost_per_call = PROVIDER_COSTS.get(provider_name, 0)
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
