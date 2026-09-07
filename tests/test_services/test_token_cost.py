"""Test token usage cost computation."""
from unittest.mock import patch

from listingjet.services.metrics import TOKEN_COSTS, record_token_usage


def test_record_token_usage_emits_cost():
    with patch("listingjet.services.metrics.emit_metric") as emit:
        record_token_usage("claude-sonnet-5", 1_000_000, 1_000_000, agent_name="social")
    # 3 metrics emitted: TokensInput, TokensOutput, EstimatedCost
    assert emit.call_count == 3
    cost_call = emit.call_args_list[2]
    in_rate, out_rate = TOKEN_COSTS["claude-sonnet-5"]
    expected = in_rate + out_rate  # 1M input + 1M output
    assert abs(cost_call.args[1] - expected) < 1e-9
    assert cost_call.kwargs["dimensions"]["model"] == "claude-sonnet-5"
    assert cost_call.kwargs["dimensions"]["agent"] == "social"


def test_record_token_usage_unknown_model_warns_once():
    with patch("listingjet.services.metrics.emit_metric") as emit:
        with patch("listingjet.services.metrics.logger") as logger:
            record_token_usage("nope-model-unique", 100, 100)
            record_token_usage("nope-model-unique", 100, 100)
    # Should emit 3 metrics per call (TokensInput, TokensOutput, EstimatedCost=0)
    # So 6 total for 2 calls
    assert emit.call_count == 6
    # Warning should only be logged once
    assert logger.warning.call_count == 1
    assert "nope-model-unique" in logger.warning.call_args[0][1]


def test_record_token_usage_without_agent():
    with patch("listingjet.services.metrics.emit_metric") as emit:
        record_token_usage("claude-haiku-4-5", 1000, 2000)
    assert emit.call_count == 3
    for call in emit.call_args_list:
        assert "agent" not in call.kwargs["dimensions"]
