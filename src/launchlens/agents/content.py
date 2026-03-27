import uuid
from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing
from launchlens.models.vision_result import VisionResult
from launchlens.providers import get_llm_provider
from launchlens.services.events import emit_event
from launchlens.services.fha_filter import fha_check
from .base import BaseAgent, AgentContext

_PROMPT_TEMPLATE = """\
Write a compelling real estate listing description for the following property.
Be specific and factual. Do not use Fair Housing Act prohibited language.

Property details:
{metadata}

Key features identified from photos:
{photo_features}

Write a 2-3 sentence description."""

_FHA_RETRY_SUFFIX = (
    "\n\nIMPORTANT: The previous attempt contained language that may violate the Fair Housing Act. "
    "Rewrite without referencing families, schools, neighborhood safety, or religion."
)


class ContentAgent(BaseAgent):
    agent_name = "content"

    def __init__(self, llm_provider=None, session_factory=None):
        self._llm_provider = llm_provider or get_llm_provider()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)

                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .where(
                        Asset.listing_id == listing_id,
                        VisionResult.tier == 1,
                    )
                    .order_by(VisionResult.quality_score.desc())
                    .limit(5)
                )
                vrs = result.scalars().all()
                features_text = ", ".join(
                    f"{vr.room_label} (q={vr.quality_score})" for vr in vrs if vr.room_label
                )

                prompt = _PROMPT_TEMPLATE.format(
                    metadata=str(listing.metadata_),
                    photo_features=features_text or "modern interior",
                )

                copy = await self._llm_provider.complete(
                    prompt=prompt, context=listing.metadata_
                )
                fha_result = fha_check({"copy": copy})

                if not fha_result.passed:
                    copy = await self._llm_provider.complete(
                        prompt=prompt + _FHA_RETRY_SUFFIX, context=listing.metadata_
                    )
                    fha_result = fha_check({"copy": copy})

                await emit_event(
                    session=session,
                    event_type="content.completed",
                    payload={"fha_passed": fha_result.passed, "copy_length": len(copy)},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"copy": copy, "fha_passed": fha_result.passed}


@activity.defn
async def run_content(listing_id: str, tenant_id: str) -> dict:
    agent = ContentAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
