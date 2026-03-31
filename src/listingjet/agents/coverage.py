import uuid
from collections import Counter

from sqlalchemy import select
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing
from listingjet.models.vision_result import VisionResult
from listingjet.services.events import emit_event

from .base import AgentContext, BaseAgent

REQUIRED_SHOTS = {"exterior", "living_room", "kitchen", "bedroom", "bathroom"}

# Room labels that count as bedrooms/bathrooms
_BEDROOM_LABELS = {"bedroom", "primary_bedroom", "master_bed", "master_bedroom"}
_BATHROOM_LABELS = {"bathroom", "primary_bathroom", "master_bath", "master_bathroom"}


class CoverageAgent(BaseAgent):
    agent_name = "coverage"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)

                # Load Tier 1 VisionResults for this listing
                result = await session.execute(
                    select(VisionResult)
                    .join(Asset, VisionResult.asset_id == Asset.id)
                    .where(
                        Asset.listing_id == listing_id,
                        VisionResult.tier == 1,
                        VisionResult.room_label.isnot(None),
                    )
                )
                vision_results = result.scalars().all()

                covered = {vr.room_label for vr in vision_results}
                room_counts = Counter(vr.room_label for vr in vision_results)
                missing = sorted(REQUIRED_SHOTS - covered)

                # Metadata vs Vision mismatch detection
                mismatches = []
                if listing and listing.metadata_:
                    meta = listing.metadata_
                    vision_beds = sum(room_counts.get(label, 0) for label in _BEDROOM_LABELS)
                    vision_baths = sum(room_counts.get(label, 0) for label in _BATHROOM_LABELS)
                    meta_beds = meta.get("beds", 0) or 0
                    meta_baths = meta.get("baths", 0) or 0

                    if meta_beds and vision_beds < meta_beds:
                        mismatches.append({
                            "type": "bedroom_count",
                            "expected": meta_beds,
                            "found": vision_beds,
                            "message": f"Listing claims {meta_beds} bedrooms but only {vision_beds} found in photos.",
                        })
                    if meta_baths and vision_baths < meta_baths:
                        mismatches.append({
                            "type": "bathroom_count",
                            "expected": meta_baths,
                            "found": vision_baths,
                            "message": f"Listing claims {meta_baths} bathrooms but only {vision_baths} found in photos.",
                        })

                if missing:
                    await emit_event(
                        session=session,
                        event_type="coverage.gap",
                        payload={"missing_shots": missing},
                        tenant_id=context.tenant_id,
                        listing_id=context.listing_id,
                    )

                if mismatches:
                    await emit_event(
                        session=session,
                        event_type="coverage.mismatch",
                        payload={"mismatches": mismatches},
                        tenant_id=context.tenant_id,
                        listing_id=context.listing_id,
                    )

        return {
            "missing_shots": missing,
            "covered_shots": sorted(covered & REQUIRED_SHOTS),
            "mismatches": mismatches,
        }
