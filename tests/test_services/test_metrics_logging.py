import logging

from listingjet.services import metrics


def test_record_cost_logs_a_metric_line(caplog):
    with caplog.at_level(logging.INFO, logger="listingjet.services.metrics"):
        metrics.record_cost("photo_analysis", "claude", 3)
    assert any("metric" in r.message and "photo_analysis" in r.message for r in caplog.records)


def test_step_timer_logs_duration(caplog):
    with caplog.at_level(logging.INFO, logger="listingjet.services.metrics"):
        with metrics.StepTimer("packaging"):
            pass
    assert any("packaging" in r.message for r in caplog.records)


def test_record_token_usage_logs_cost_correctly(caplog):
    """Test that record_token_usage logs EstimatedCost with correct calculation."""
    with caplog.at_level(logging.INFO, logger="listingjet.services.metrics"):
        metrics.record_token_usage("claude-haiku-4-5", 1000, 100, "photo_analysis")

    # Find the EstimatedCost metric line
    cost_lines = [r for r in caplog.records if "EstimatedCost" in r.message]
    assert len(cost_lines) == 1

    # Expected cost: 1000 * 1.00 / 1e6 + 100 * 5.00 / 1e6 = 0.001 + 0.0005 = 0.0015
    cost_line = cost_lines[0]
    assert "0.0015" in cost_line.message


def test_record_token_usage_unknown_id_warns_once(caplog):
    """Test that unknown model id logs WARNING and still records metrics with cost 0."""
    # Clear the module-level warning set to start fresh
    metrics._warned_unknown_model_ids.clear()

    with caplog.at_level(logging.DEBUG, logger="listingjet.services.metrics"):
        metrics.record_token_usage("nope-model", 1000, 100, "test")
        metrics.record_token_usage("nope-model", 1000, 100, "test")

    # Find warning and metric lines
    warning_lines = [r for r in caplog.records if r.levelname == "WARNING"]
    metric_lines = [r for r in caplog.records if "metric" in r.message and "nope-model" in r.message]

    # Should warn only once
    assert len(warning_lines) == 1
    assert "nope-model" in warning_lines[0].message

    # Should log metrics twice (once per call), with EstimatedCost 0
    cost_lines = [r for r in metric_lines if "EstimatedCost" in r.message]
    assert len(cost_lines) == 2
    for cost_line in cost_lines:
        assert "value=0" in cost_line.message or "value=0.0" in cost_line.message
