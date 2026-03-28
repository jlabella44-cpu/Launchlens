import json
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
from launchlens.services.metrics import record_cost

from .base import AgentContext, BaseAgent

_PROMPT_TEMPLATE = """\
Write two real estate listing descriptions for the following property.
Be specific and factual. Do not use Fair Housing Act prohibited language.

Property details:
{metadata}

Key features identified from photos:
{photo_features}

Return ONLY a JSON object with this exact structure:
{{
  "mls_safe": "...(2-3 sentences, factual only, no agent promotion, no personality)...",
  "marketing": "...(2-3 sentences, compelling, personality allowed, but still FHA compliant)..."
}}"""

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

                raw = await self._llm_provider.complete(
                    prompt=prompt, context=listing.metadata_
                )
                parsed = json.loads(raw)
                mls_safe = parsed["mls_safe"]
                marketing = parsed["marketing"]
                fha_result = fha_check({"mls_safe": mls_safe, "marketing": marketing})

                if not fha_result.passed:
                    raw = await self._llm_provider.complete(
                        prompt=prompt + _FHA_RETRY_SUFFIX, context=listing.metadata_
                    )
                    parsed = json.loads(raw)
                    mls_safe = parsed["mls_safe"]
                    marketing = parsed["marketing"]
                    fha_result = fha_check({"mls_safe": mls_safe, "marketing": marketing})

                await emit_event(
                    session=session,
                    event_type="content.completed",
                    payload={
                        "fha_passed": fha_result.passed,
                        "mls_safe_length": len(mls_safe),
                        "marketing_length": len(marketing),
                    },
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        llm_calls = 2 if not fha_result.passed else 1
        record_cost(self.agent_name, "claude", llm_calls)
        return {"mls_safe": mls_safe, "marketing": marketing, "fha_passed": fha_result.passed}


@activity.defn
async def run_content(listing_id: str, tenant_id: str) -> dict:
    agent = ContentAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.instrumented_execute(ctx)
