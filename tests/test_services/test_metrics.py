import logging

from listingjet.services import metrics


def test_record_video_seconds_known_model():
    cost = metrics.record_video_seconds("gen4_turbo", 5.0, "video_ai")
    assert cost == 0.25


def test_record_video_seconds_unknown_model_warns_once(caplog):
    metrics._warned_unknown_model_ids.clear()

    with caplog.at_level(logging.DEBUG, logger="listingjet.services.metrics"):
        first = metrics.record_video_seconds("nope-model", 5.0, "video_ai")
        second = metrics.record_video_seconds("nope-model", 5.0, "video_ai")

    assert first == 0.0
    assert second == 0.0

    warning_lines = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warning_lines) == 1
    assert "nope-model" in warning_lines[0].message
