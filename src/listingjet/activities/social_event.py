"""Pipeline activity: create a just_listed event after pipeline completion."""
import logging
from temporalio import activity
from listingjet.agents.base import AgentContext

logger = logging.getLogger(__name__)

@activity.defn
async def run_social_event(context: AgentContext) -> dict:
    """Create a just_listed listing event and trigger social reminders."""
    from listingjet.database import get_async_session
    from listingjet.models.listing import Listing
    from listingjet.models.listing_event import ListingEvent
    from listingjet.models.user import User, UserRole
    from listingjet.services.post_time_config import find_next_post_window, get_listing_timezone
    from listingjet.services.social_reminder import SocialReminderService
    from sqlalchemy import select
    from datetime import datetime, timezone as tz_mod

    async with get_async_session() as session:
        listing = (await session.execute(
            select(Listing).where(Listing.id == context.listing_id)
        )).scalar_one_or_none()
        if not listing:
            return {"status": "listing_not_found"}

        existing = (await session.execute(
            select(ListingEvent).where(
                ListingEvent.listing_id == listing.id,
                ListingEvent.event_type == "just_listed",
            ).limit(1)
        )).scalar_one_or_none()
        if existing:
            return {"status": "already_exists", "event_id": str(existing.id)}

        event = ListingEvent(
            tenant_id=listing.tenant_id, listing_id=listing.id,
            event_type="just_listed", event_data={},
        )
        session.add(event)
        await session.flush()

        admin = (await session.execute(
            select(User).where(User.tenant_id == listing.tenant_id, User.role == UserRole.ADMIN).limit(1)
        )).scalar_one_or_none()

        if admin:
            address = listing.address.get("street", "your listing")
            state_code = listing.address.get("state", "NY")
            tz = get_listing_timezone(state_code)
            now = datetime.now(tz)
            next_window = find_next_post_window("instagram", now)

            svc = SocialReminderService()
            if next_window is None:
                svc.create_notification(
                    session=session, user_id=admin.id, tenant_id=listing.tenant_id,
                    listing_id=listing.id, event_type="just_listed", address=address,
                )
                event.notified_at = datetime.now(tz_mod.utc)
                await svc.send_email_reminder(
                    to_email=admin.email, listing_id=listing.id, event_id=event.id,
                    event_type="just_listed", address=address,
                )

        await session.commit()
        return {"status": "created", "event_id": str(event.id)}
