"""Smoke test the Resend email provider end-to-end.

Sends a real email via the ListingJet email service factory. Use this after
rotating RESEND_API_KEY or changing email config to verify delivery before
trusting any pipeline email.

Usage:
    python scripts/smoke_resend.py <recipient@example.com>

Requires RESEND_API_KEY and EMAIL_ENABLED=true in the environment (or .env).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/smoke_resend.py <recipient@example.com>", file=sys.stderr)
        return 2

    to = sys.argv[1]

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

    from listingjet.config import settings
    from listingjet.services.email import ResendEmailService, get_email_service

    print(f"email_enabled:   {settings.email_enabled}")
    print(f"resend_key_set:  {bool(settings.resend_api_key)}")
    print(f"email_from:      {settings.email_from}")

    if not settings.resend_api_key:
        print("FAIL: RESEND_API_KEY is not set", file=sys.stderr)
        return 1
    if not settings.email_enabled:
        print("FAIL: EMAIL_ENABLED is false — the factory would return NoOp", file=sys.stderr)
        return 1

    service = get_email_service()
    if not isinstance(service, ResendEmailService):
        print(f"FAIL: factory returned {type(service).__name__}, expected ResendEmailService", file=sys.stderr)
        return 1

    timestamp = datetime.now(timezone.utc).isoformat()
    subject = f"[smoke] ListingJet Resend test — {timestamp}"
    html = f"""
    <html><body style="font-family:sans-serif">
    <h2>Resend smoke test</h2>
    <p>If you received this, Resend is correctly wired into ListingJet.</p>
    <ul>
      <li><strong>Sender:</strong> {settings.email_from}</li>
      <li><strong>Timestamp:</strong> {timestamp}</li>
      <li><strong>Environment:</strong> {os.environ.get('APP_ENV', 'local')}</li>
    </ul>
    </body></html>
    """

    print(f"\nsending to:      {to}")
    try:
        service.send(to=to, subject=subject, html_body=html)
    except Exception as exc:
        print(f"FAIL: send raised {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print("OK — check the recipient inbox (and spam folder) within 60s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
