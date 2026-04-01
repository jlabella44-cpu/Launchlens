import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from listingjet.agents.base import AgentContext, BaseAgent
from listingjet.config import settings
from listingjet.database import AsyncSessionLocal
from listingjet.models.listing import Listing
from listingjet.models.property_data import PropertyData
from listingjet.services.property_scraper import run_all_scrapers
from listingjet.services.property_scraper.cross_reference import cross_reference


class PropertyVerificationAgent(BaseAgent):
    agent_name = "property_verification"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
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

                # 4. Get the Listing to extract address string
                listing = await session.get(Listing, listing_id)
                if listing is None:
                    return {"verification_status": "skipped"}

                addr = listing.address or {}
                parts = [
                    addr.get("street", ""),
                    addr.get("city", ""),
                    addr.get("state", ""),
                    addr.get("zip", ""),
                ]
                address_str = ", ".join(p for p in parts if p).strip(", ")

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

                # 6. Run all scrapers
                scraped = await run_all_scrapers(address_str)

                # 7. Cross-reference
                xref = cross_reference(api_data, scraped)

                # 8. Update PropertyData
                property_data.verification_status = xref["status"]
                property_data.field_confidence = xref["field_confidence"]
                property_data.mismatches = xref["mismatches"]
                property_data.scraped_data = scraped
                property_data.sources_checked = xref["sources_checked"]
                property_data.verified_at = datetime.now(timezone.utc)

        # 9. Return result
        return {
            "verification_status": xref["status"],
            "field_confidence": xref["field_confidence"],
            "mismatches": xref["mismatches"],
            "sources_checked": xref["sources_checked"],
        }
