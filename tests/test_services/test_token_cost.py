"""Test token usage cost computation."""
from unittest.mock import patch

from listingjet.services.metrics import TOKEN_COSTS, record_token_usage


def test_record_token_usage_emits_cost():
    with patch("listingjet.services.metrics.emit_metric") as emit:
        record_token_usage("gemma", 1_000_000, 1_000_000, agent_name="social")
    # 3 metrics emitted: TokensInput, TokensOutput, EstimatedCost
    assert emit.call_count == 3
    cost_call = emit.call_args_list[2]
    in_rate, out_rate = TOKEN_COSTS["gemma"]
    expected = in_rate + out_rate  # 1M input + 1M output
    assert abs(cost_call.args[1] - expected) < 1e-9
    assert cost_call.kwargs["dimensions"]["provider"] == "gemma"
    assert cost_call.kwargs["dimensions"]["agent"] == "social"


def test_record_token_usage_unknown_provider_noop():
    with patch("listingjet.services.metrics.emit_metric") as emit:
        record_token_usage("mystery", 100, 100)
    emit.assert_not_called()


def test_record_token_usage_without_agent():
    with patch("listingjet.services.metrics.emit_metric") as emit:
        record_token_usage("qwen", 1000, 2000)
    assert emit.call_count == 3
    for call in emit.call_args_list:
        assert "agent" not in call.kwargs["dimensions"]
