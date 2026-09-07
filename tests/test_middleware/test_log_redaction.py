"""The uvicorn access log must never carry a raw `?token=` value.

EventSource can't send an Authorization header, so the SSE endpoint accepts
`?token=<jwt>` — which uvicorn records verbatim in its access log line.
"""
import logging

import pytest

from listingjet.logging_config import RedactTokenFilter, setup_logging


def _record(msg, args=None):
    return logging.LogRecord(
        name="uvicorn.access", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=args, exc_info=None,
    )


def test_filter_redacts_token_in_uvicorn_access_line():
    """The real uvicorn access format: request line arrives via record.args."""
    record = _record(
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET",
         "/sse/listings/abc/events?token=eyJhbGciOi.PAYLOAD.SIGNATURE", "1.1", 200),
    )

    assert RedactTokenFilter().filter(record) is True

    message = record.getMessage()
    assert "token=REDACTED" in message
    assert "eyJhbGciOi" not in message
    assert "/sse/listings/abc/events" in message


def test_filter_redacts_token_in_the_message_itself():
    record = _record("GET /sse/x?foo=1&token=secret-jwt&bar=2")

    RedactTokenFilter().filter(record)

    assert record.getMessage() == "GET /sse/x?foo=1&token=REDACTED&bar=2"


def test_filter_leaves_other_records_alone():
    record = _record("nothing sensitive here")
    RedactTokenFilter().filter(record)
    assert record.getMessage() == "nothing sensitive here"


def test_filter_handles_dict_args():
    record = _record("%(path)s", ({"path": "/sse?token=abc123"},))
    RedactTokenFilter().filter(record)
    assert record.getMessage() == "/sse?token=REDACTED"


@pytest.mark.parametrize("app_env", ["development", "production"])
def test_setup_logging_installs_the_filter_once(app_env):
    setup_logging(app_env=app_env)
    setup_logging(app_env=app_env)

    access_logger = logging.getLogger("uvicorn.access")
    installed = [f for f in access_logger.filters if isinstance(f, RedactTokenFilter)]
    assert len(installed) == 1
