import uuid

from sqlalchemy import select
from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState
from launchlens.services.events import emit_event

from .base import AgentContext, BaseAgent


class IngestionAgent(BaseAgent):
    agent_name = "ingestion"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                result = await session.execute(
                    select(Asset).where(
                        Asset.listing_id == listing_id,
                        Asset.state == "uploaded",
                    )
                )
                assets = result.scalars().all()

                seen_hashes: set[str] = set()
                ingested = []
                duplicates = []

                for asset in assets:
                    if asset.file_hash in seen_hashes:
                        asset.state = "duplicate"
                        duplicates.append(asset)
                    else:
                        seen_hashes.add(asset.file_hash)
                        asset.state = "ingested"
                        ingested.append(asset)

                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.ANALYZING

                await emit_event(
                    session=session,
                    event_type="ingestion.completed",
                    payload={
                        "ingested_count": len(ingested),
                        "duplicate_count": len(duplicates),
                    },
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {"ingested_count": len(ingested), "duplicate_count": len(duplicates)}


@activity.defn
async def run_ingestion(listing_id: str, tenant_id: str) -> dict:
    agent = IngestionAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
