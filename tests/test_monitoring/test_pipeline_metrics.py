"""Tests for services/metrics.py — pipeline-level metrics."""

from unittest.mock import patch

import pytest

from listingjet.services.metrics import (
    StepTimer,
    record_cost,
    record_provider_call,
    record_review_turnaround,
    record_step_failure,
    track_step_duration,
)


def test_track_step_duration_emits_metric():
    with patch("listingjet.services.metrics.emit_metric") as mock:
        track_step_duration("ingestion", 150.5)
        mock.assert_called_once_with(
            "AgentStepDuration",
            150.5,
            unit="Milliseconds",
            dimensions={"agent": "ingestion"},
        )


def test_record_step_failure_emits_metric():
    with patch("listingjet.services.metrics.emit_metric") as mock:
        record_step_failure("vision")
        mock.assert_called_once_with(
            "AgentStepFailure",
            1,
            unit="Count",
            dimensions={"agent": "vision"},
        )


def test_record_provider_call_emits_metric():
    with patch("listingjet.services.metrics.emit_metric") as mock:
        record_provider_call("google_vision", True)
        mock.assert_called_once_with(
            "ProviderCallCount",
            1,
            unit="Count",
            dimensions={"provider": "google_vision", "success": "True"},
        )


def test_record_provider_call_failure():
    with patch("listingjet.services.metrics.emit_metric") as mock:
        record_provider_call("claude", False)
        mock.assert_called_once_with(
            "ProviderCallCount",
            1,
            unit="Count",
            dimensions={"provider": "claude", "success": "False"},
        )


def test_record_cost_emits_metric():
    with patch("listingjet.services.metrics.emit_metric") as mock:
        record_cost("vision", "google_vision", 10)
        mock.assert_called_once_with(
            "EstimatedCost",
            0.2,  # 10 * 0.02
            unit="None",
            dimensions={"agent": "vision", "provider": "google_vision"},
        )


def test_record_cost_unknown_provider():
    with patch("listingjet.services.metrics.emit_metric") as mock:
        record_cost("test", "unknown_provider", 1)
        mock.assert_not_called()


def test_record_review_turnaround():
    with patch("listingjet.services.metrics.emit_metric") as mock:
        record_review_turnaround(3600.0)
        mock.assert_called_once_with(
            "ReviewTurnaround",
            3600.0,
            unit="Seconds",
            dimensions={},
        )


def test_step_timer_records_duration():
    with patch("listingjet.services.metrics.track_step_duration") as mock_dur:
        with StepTimer("test_agent"):
            pass
        mock_dur.assert_called_once()
        assert mock_dur.call_args[0][0] == "test_agent"
        assert mock_dur.call_args[0][1] >= 0


def test_step_timer_records_failure_on_exception():
    with patch("listingjet.services.metrics.track_step_duration"):
        with patch("listingjet.services.metrics.record_step_failure") as mock_fail:
            with pytest.raises(RuntimeError):
                with StepTimer("test_agent"):
                    raise RuntimeError("boom")
            mock_fail.assert_called_once_with("test_agent")
