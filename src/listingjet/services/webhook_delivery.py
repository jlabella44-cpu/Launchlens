"""
Webhook delivery service.

Sends event payloads to tenant webhook URLs via HTTP POST.
Includes HMAC signature for verification, retry with backoff.
"""
import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from listingjet.config import settings
from listingjet.utils.retry import async_retry

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0

# Private/reserved IP networks that webhooks must never target (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_url_safe(url: str) -> bool:
    """Validate that a webhook URL targets a public IP, not internal/private ranges."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Resolve hostname to IP and check against blocked ranges
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            for network in _BLOCKED_NETWORKS:
                if ip in network:
                    return False
        return True
    except (socket.gaierror, ValueError):
        return False


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
      X-ListingJet-Event: event_type
      X-ListingJet-Timestamp: ISO timestamp
      X-ListingJet-Signature: HMAC-SHA256
      Content-Type: application/json
    """
    if not _is_url_safe(url):
        logger.warning("webhook.blocked_ssrf url=%s tenant=%s", url, tenant_id)
        return False

    body = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "listing_id": listing_id,
        "data": payload,
    }
    body_bytes = json.dumps(body).encode()
    # Use a per-tenant HMAC key derived from the app secret + tenant_id
    webhook_secret = hmac.new(
        settings.jwt_secret.encode(), tenant_id.encode(), hashlib.sha256
    ).hexdigest()
    signature = _sign_payload(body_bytes, webhook_secret)

    headers = {
        "Content-Type": "application/json",
        "X-ListingJet-Event": event_type,
        "X-ListingJet-Timestamp": body["timestamp"],
        "X-ListingJet-Signature": f"sha256={signature}",
        "User-Agent": "ListingJet-Webhook/1.0",
    }

    @async_retry(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        retry_on=(httpx.HTTPError, httpx.TimeoutException),
    )
    async def _post_with_retry() -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, content=body_bytes, headers=headers, timeout=_TIMEOUT
            )
            resp.raise_for_status()
            logger.info(
                "webhook.delivered url=%s event=%s status=%d",
                url, event_type, resp.status_code,
            )
            return True

    try:
        return await _post_with_retry()
    except Exception:
        logger.error("webhook.exhausted url=%s event=%s after retries", url, event_type)
        return False
