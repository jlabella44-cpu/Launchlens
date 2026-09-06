import logging

from listingjet.services import metrics


def test_record_cost_logs_a_metric_line(caplog):
    with caplog.at_level(logging.INFO, logger="listingjet.services.metrics"):
        metrics.record_cost("vision", "google_vision", 3)
    assert any("metric" in r.message and "vision" in r.message for r in caplog.records)


def test_step_timer_logs_duration(caplog):
    with caplog.at_level(logging.INFO, logger="listingjet.services.metrics"):
        with metrics.StepTimer("packaging"):
            pass
    assert any("packaging" in r.message for r in caplog.records)
