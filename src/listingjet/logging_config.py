"""
Structured JSON logging configuration.

In production (app_env != "development"), logs are emitted as JSON lines
for ingestion by log aggregators (CloudWatch, Datadog, etc.).

In development, uses standard human-readable format.
"""
import json
import logging
import re
import sys
from datetime import datetime, timezone

# `?token=<jwt>` is accepted by the SSE endpoint (EventSource cannot send
# custom headers), and uvicorn's access log records the whole request line —
# so the raw JWT would otherwise land in the logs.
_TOKEN_RE = re.compile(r"(token=)[^&\s\"'#]+", re.IGNORECASE)


def redact_tokens(value):
    """Replace any `token=<value>` inside a string with `token=REDACTED`."""
    if isinstance(value, str) and "token=" in value.lower():
        return _TOKEN_RE.sub(r"\1REDACTED", value)
    return value


class RedactTokenFilter(logging.Filter):
    """Strips query-string tokens from log records. Never drops a record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_tokens(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(redact_tokens(a) for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: redact_tokens(v) for k, v in record.args.items()}
        return True


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Include extra fields if set (e.g., request_id, tenant_id)
        for key in ("request_id", "tenant_id", "listing_id", "event_type"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        return json.dumps(log_entry)


def setup_logging(app_env: str = "development", log_level: str = "INFO"):
    """Configure root logger based on environment."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if app_env == "development":
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")
        )
    else:
        handler.setFormatter(JSONFormatter())

    root.addHandler(handler)

    # Quiet noisy libraries
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.setLevel(logging.WARNING)
    if not any(isinstance(f, RedactTokenFilter) for f in access_logger.filters):
        access_logger.addFilter(RedactTokenFilter())
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
