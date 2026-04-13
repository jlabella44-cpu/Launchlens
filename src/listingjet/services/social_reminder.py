"""Social reminder service — creates notifications and sends emails for listing events."""
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.notification import Notification

logger = logging.getLogger(__name__)
_FOLLOWUP_DELAY_HOURS = 24

class SocialReminderService:
    def create_notification(self, session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID,
                            listing_id: uuid.UUID, event_type: str, address: str) -> Notification:
        event_labels = {"just_listed": "Just Listed", "open_house": "Open House",
                        "price_change": "Price Change", "sold_pending": "Sold/Pending"}
        label = event_labels.get(event_type, event_type)
        notif = Notification(
            tenant_id=tenant_id, user_id=user_id, type="social_reminder",
            title=f"{label}: {address}",
            body=f"Your listing at {address} is ready to share on social media. Best time to post is now!",
            action_url=f"/listings/{listing_id}/social",
        )
        session.add(notif)
        return notif

    async def send_email_reminder(self, to_email: str, listing_id: uuid.UUID, event_id: uuid.UUID,
                                   event_type: str, address: str, is_followup: bool = False) -> None:
        try:
            from listingjet.services.email import get_email_service
            email_svc = get_email_service()
            template = "social_reminder_followup" if is_followup else "social_reminder"
            email_svc.send_notification(
                to_email, template, address=address, event_type=event_type,
                listing_id=str(listing_id), event_id=str(event_id),
                social_url=f"https://listingjet.ai/listings/{listing_id}/social?event={event_id}",
            )
        except Exception:
            logger.exception("social_reminder email failed for listing %s", listing_id)

    def should_send_followup(self, event, now: datetime) -> bool:
        if event.followup_sent_at is not None:
            return False
        if len(event.posted_platforms) > 0:
            return False
        if event.notified_at is None:
            return False
        return (now - event.notified_at) >= timedelta(hours=_FOLLOWUP_DELAY_HOURS)
