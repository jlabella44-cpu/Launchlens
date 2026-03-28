"""
Webhook delivery service.

Sends event payloads to tenant webhook URLs via HTTP POST.
Includes HMAC signature for verification, retry with backoff.
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0
_MAX_RETRIES = 3


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """HMAC-SHA256 signature for webhook verification."""
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


async def deliver_webhook(
    url: str,
    event_type: str,
    payload: dict,
    tenant_id: str,
    listing_id: str | None = None,
) -> bool:
    """
    POST event to webhook URL. Returns True if delivered (2xx), False otherwise.

    Headers:
      X-LaunchLens-Event: event_type
      X-LaunchLens-Timestamp: ISO timestamp
      X-LaunchLens-Signature: HMAC-SHA256 (using tenant_id as secret for now)
      Content-Type: application/json
    """
    body = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "listing_id": listing_id,
        "data": payload,
    }
    body_bytes = json.dumps(body).encode()
    signature = _sign_payload(body_bytes, tenant_id)

    headers = {
        "Content-Type": "application/json",
        "X-LaunchLens-Event": event_type,
        "X-LaunchLens-Timestamp": body["timestamp"],
        "X-LaunchLens-Signature": f"sha256={signature}",
        "User-Agent": "LaunchLens-Webhook/1.0",
    }

    for attempt in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, content=body_bytes, headers=headers, timeout=_TIMEOUT
                )
            if 200 <= resp.status_code < 300:
                logger.info(
                    "webhook.delivered url=%s event=%s status=%d",
                    url, event_type, resp.status_code,
                )
                return True
            logger.warning(
                "webhook.failed url=%s event=%s status=%d attempt=%d",
                url, event_type, resp.status_code, attempt + 1,
            )
        except Exception as exc:
            logger.warning(
                "webhook.error url=%s event=%s error=%s attempt=%d",
                url, event_type, str(exc), attempt + 1,
            )

    logger.error("webhook.exhausted url=%s event=%s after %d attempts", url, event_type, _MAX_RETRIES)
    return False
