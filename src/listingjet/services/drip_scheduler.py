"""
Drip email scheduler — sends timed welcome sequence emails to new users.

Schedule: Run this as a periodic task (e.g., Temporal cron or celery beat) once per day.
It queries users by registration date and sends the appropriate drip email.

Drip sequence:
  - welcome_drip_1: Sent immediately on registration (handled in auth.py)
  - welcome_drip_2: Day 1 after registration
  - welcome_drip_3: Day 3 after registration
  - welcome_drip_4: Day 5 after registration
  - welcome_drip_5: Day 10 after registration
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.user import User
from listingjet.services.email import get_email_service

logger = logging.getLogger(__name__)

# (days_since_registration, template_name) — drip_1 sent inline at registration
DRIP_SCHEDULE = [
    (1, "welcome_drip_2"),
    (3, "welcome_drip_3"),
    (5, "welcome_drip_4"),
    (10, "welcome_drip_5"),
]

APP_URL = "https://app.listingjet.com"


async def run_drip_emails(db: AsyncSession) -> int:
    """Send pending drip emails for all users. Returns count of emails sent."""
    now = datetime.now(timezone.utc)
    email_svc = get_email_service()
    sent_count = 0

    for days, template_name in DRIP_SCHEDULE:
        # Find users who registered exactly `days` ago (within a 24h window)
        window_start = now - timedelta(days=days, hours=12)
        window_end = now - timedelta(days=days - 1, hours=12)

        result = await db.execute(
            select(User).where(
                User.consent_at >= window_start,
                User.consent_at < window_end,
            )
        )
        users = result.scalars().all()

        for user in users:
            try:
                context = {
                    "name": user.name or "there",
                    "upload_url": f"{APP_URL}/listings",
                    "listing_url": f"{APP_URL}/listings",
                    "upgrade_url": f"{APP_URL}/pricing",
                }
                email_svc.send_notification(user.email, template_name, **context)
                sent_count += 1
                logger.info("drip_sent template=%s user=%s", template_name, user.email)
            except Exception:
                logger.exception("drip_failed template=%s user=%s", template_name, user.email)

    return sent_count
