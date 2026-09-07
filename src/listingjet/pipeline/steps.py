"""One async callable per pipeline step. Each wraps an existing agent unchanged.

Replaces activities/pipeline.py and activities/social_event.py.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from listingjet.agents.base import AgentContext
from listingjet.agents.brand import BrandAgent
from listingjet.agents.content import ContentAgent
from listingjet.agents.coverage import CoverageAgent
from listingjet.agents.distribution import DistributionAgent
from listingjet.agents.dollhouse_render import DollhouseRenderAgent
from listingjet.agents.floorplan import FloorplanAgent
from listingjet.agents.health_score import HealthScoreAgent
from listingjet.agents.ingestion import IngestionAgent
from listingjet.agents.learning import LearningAgent
from listingjet.agents.microsite_generator import MicrositeGeneratorAgent
from listingjet.agents.mls_export import MLSExportAgent
from listingjet.agents.packaging import PackagingAgent
from listingjet.agents.performance_intelligence import PerformanceIntelligenceAgent
from listingjet.agents.photo_analysis import PhotoAnalysisAgent
from listingjet.agents.property_verification import PropertyVerificationAgent
from listingjet.agents.social_content import SocialContentAgent
from listingjet.agents.social_cuts import SocialCutAgent
from listingjet.agents.video import VideoAgent
from listingjet.agents.virtual_staging import VirtualStagingAgent
from listingjet.database import admin_session

logger = logging.getLogger(__name__)


@dataclass
class StepContext:
    listing_id: str
    tenant_id: str
    results: dict[str, dict] = field(default_factory=dict)

    def agent_context(self) -> AgentContext:
        return AgentContext(listing_id=self.listing_id, tenant_id=self.tenant_id)


StepFn = Callable[[StepContext], Awaitable[dict]]


def _agent_step(agent_cls) -> StepFn:
    async def run(ctx: StepContext) -> dict:
        agent = agent_cls(session_factory=admin_session)
        result = await agent.instrumented_execute(ctx.agent_context())
        return result if isinstance(result, dict) else {"result": result}
    run.__name__ = f"run_{agent_cls.agent_name}"
    return run


async def run_mls_export(ctx: StepContext) -> dict:
    brand = ctx.results.get("brand") or {}
    agent = MLSExportAgent(
        content_result=ctx.results.get("content") or {},
        flyer_s3_key=brand.get("flyer_s3_key"),
        session_factory=admin_session,
    )
    return await agent.instrumented_execute(ctx.agent_context())


async def run_social_event(ctx: StepContext) -> dict:
    """Create a just_listed listing event and trigger social reminders.

    Ported from activities/social_event.py; that module imported a
    non-existent `get_async_session`, so this step has never succeeded.
    """
    from datetime import datetime
    from datetime import timezone as tz_mod

    from sqlalchemy import select

    from listingjet.models.listing import Listing
    from listingjet.models.listing_event import ListingEvent
    from listingjet.models.user import User, UserRole
    from listingjet.services.post_time_config import find_next_post_window, get_listing_timezone
    from listingjet.services.social_reminder import SocialReminderService

    async with admin_session() as session:
        listing = (await session.execute(
            select(Listing).where(Listing.id == ctx.listing_id)
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


STEP_FUNCTIONS: dict[str, StepFn] = {
    "ingestion": _agent_step(IngestionAgent),
    "photo_analysis": _agent_step(PhotoAnalysisAgent),
    "property_verification": _agent_step(PropertyVerificationAgent),
    "coverage": _agent_step(CoverageAgent),
    "virtual_staging": _agent_step(VirtualStagingAgent),
    "floorplan": _agent_step(FloorplanAgent),
    "dollhouse_render": _agent_step(DollhouseRenderAgent),
    "packaging": _agent_step(PackagingAgent),
    "video": _agent_step(VideoAgent),
    "content": _agent_step(ContentAgent),
    "brand": _agent_step(BrandAgent),
    "social_content": _agent_step(SocialContentAgent),
    "social_cuts": _agent_step(SocialCutAgent),
    "mls_export": run_mls_export,
    "distribution": _agent_step(DistributionAgent),
    "microsite": _agent_step(MicrositeGeneratorAgent),
    "learning": _agent_step(LearningAgent),
    "social_event": run_social_event,
    "health_score": _agent_step(HealthScoreAgent),
    "performance_intelligence": _agent_step(PerformanceIntelligenceAgent),
}
