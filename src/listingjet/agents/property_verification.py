from datetime import datetime, timezone

from sqlalchemy import select

from listingjet.agents.base import AgentContext, BaseAgent
from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.models.listing import Listing
from listingjet.models.property_data import PropertyData


class PropertyVerificationAgent(BaseAgent):
    agent_name = "property_verification"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
                # 1. Get PropertyData record for this listing_id
                result = await session.execute(
                    select(PropertyData).where(PropertyData.listing_id == listing_id)
                )
                property_data = result.scalar_one_or_none()

                # 2. If no record or never_listed → skip
                if property_data is None or property_data.property_status == "never_listed":
                    return {"verification_status": "skipped"}

                # 3. Check feature flag
                if not settings.property_verification_enabled:
                    return {"verification_status": "skipped"}

                # 4. Confirm the Listing exists
                listing = await session.get(Listing, listing_id)
                if listing is None:
                    return {"verification_status": "skipped"}

                # 5. Build api_data dict from PropertyData fields
                api_data = {
                    k: v for k, v in {
                        "beds": property_data.beds,
                        "baths": property_data.baths,
                        "sqft": property_data.sqft,
                        "lot_sqft": property_data.lot_sqft,
                        "year_built": property_data.year_built,
                    }.items() if v is not None
                }

                # Verification from API data only (site scrapers were removed in Phase 3).
                property_data.verification_status = "api_only" if api_data else "unverified"
                # ATTOM is a single, uncorroborated data source with no
                # cross-check against a second provider or scraper, so we
                # can't claim full confidence — 0.5 reflects "unverified but
                # plausible" rather than confirmed accuracy.
                property_data.field_confidence = {k: 0.5 for k in api_data}
                property_data.mismatches = []
                property_data.scraped_data = {}
                property_data.sources_checked = ["attom"] if api_data else []
                property_data.verified_at = datetime.now(timezone.utc)
                xref = {"status": property_data.verification_status,
                        "field_confidence": property_data.field_confidence,
                        "mismatches": [], "sources_checked": property_data.sources_checked}

        # 9. Return result
        return {
            "verification_status": xref["status"],
            "field_confidence": xref["field_confidence"],
            "mismatches": xref["mismatches"],
            "sources_checked": xref["sources_checked"],
        }
