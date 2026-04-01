import logging
import uuid

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.listing import Listing, ListingState
from listingjet.models.performance_event import PerformanceEvent
from listingjet.services.events import emit_event

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)


class DistributionAgent(BaseAgent):
    agent_name = "distribution"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.DELIVERED

                await emit_event(
                    session=session,
                    event_type="pipeline.completed",
                    payload={"listing_id": context.listing_id},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

                # Record performance event for learning loop
                session.add(PerformanceEvent(
                    tenant_id=uuid.UUID(context.tenant_id),
                    listing_id=listing_id,
                    signal_type="listing_delivered",
                    value=1.0,
                    source="pipeline",
                ))

                # Send pipeline-complete notification email
                from listingjet.services.notifications import notify_pipeline_complete
                await notify_pipeline_complete(session, listing, context.tenant_id)

                # Send LISTING_DELIVERED email to tenant admin
                try:
                    from listingjet.models.user import User, UserRole
                    from listingjet.services.email import get_email_service
                    from listingjet.services.notifications import _listing_address_str
                    admin_result = await session.execute(
                        select(User).where(
                            User.tenant_id == uuid.UUID(context.tenant_id),
                            User.role == UserRole.ADMIN,
                        ).limit(1)
                    )
                    admin_user = admin_result.scalar_one_or_none()
                    if admin_user:
                        address = _listing_address_str(listing)
                        email_svc = get_email_service()
                        email_svc.send_notification(
                            admin_user.email,
                            "listing_delivered",
                            name=admin_user.name or "there",
                            address=address,
                            download_url=f"https://app.listingjet.com/listings/{context.listing_id}/download",
                            listing_url=f"https://app.listingjet.com/listings/{context.listing_id}",
                        )
                except Exception:
                    logger.exception("listing_delivered email failed for listing %s", context.listing_id)

        return {"status": "delivered"}
