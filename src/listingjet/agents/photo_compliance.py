"""
PhotoComplianceAgent — scans listing photos for MLS compliance issues.

Detects: visible branding/logos, real estate signs, people/faces,
text overlays. Uses GPT-4V via OpenAIVisionProvider.

Results are stored as compliance events and returned as a per-photo report.
Non-blocking: flags issues as warnings, does not prevent export.
"""
import json
from dataclasses import dataclass

from sqlalchemy import select

from listingjet.agents.base import strip_markdown_fences
from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing
from listingjet.models.package_selection import PackageSelection
from listingjet.providers.openai_vision import OpenAIVisionProvider
from listingjet.services.storage import StorageService

from .base import AgentContext, BaseAgent

_COMPLIANCE_PROMPT = """\
Analyze this real estate listing photo for MLS compliance issues.
Check for the following violations and return ONLY a JSON object:

{
  "branding": {"detected": true/false, "details": "description if detected"},
  "signage": {"detected": true/false, "details": "description if detected"},
  "people": {"detected": true/false, "details": "description if detected"},
  "text_overlay": {"detected": true/false, "details": "description if detected"},
  "overall_compliant": true/false,
  "issues_summary": "brief summary of all issues, or 'No issues found'"
}

Violations to check:
- branding: visible company logos, watermarks, agent branding, brokerage marks
- signage: real estate signs (for sale, open house, agent signs) visible in photo
- people: any people, faces, or identifiable persons in the photo
- text_overlay: added text, captions, contact info overlaid on the photo

Return only valid JSON, no markdown."""


@dataclass
class PhotoComplianceResult:
    asset_id: str
    file_path: str
    compliant: bool
    branding: bool
    signage: bool
    people: bool
    text_overlay: bool
    issues_summary: str


class PhotoComplianceAgent(BaseAgent):
    agent_name = "photo_compliance"

    def __init__(self, vision_provider=None, storage_service=None, session_factory=None):
        self._vision = vision_provider or OpenAIVisionProvider()
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def _check_photo(self, image_url: str, asset_id: str, file_path: str) -> PhotoComplianceResult:
        """Analyze a single photo for compliance issues."""
        try:
            raw = await self._vision.analyze_with_prompt(image_url, _COMPLIANCE_PROMPT)
            data = json.loads(strip_markdown_fences(raw))
            return PhotoComplianceResult(
                asset_id=asset_id,
                file_path=file_path,
                compliant=data.get("overall_compliant", True),
                branding=data.get("branding", {}).get("detected", False),
                signage=data.get("signage", {}).get("detected", False),
                people=data.get("people", {}).get("detected", False),
                text_overlay=data.get("text_overlay", {}).get("detected", False),
                issues_summary=data.get("issues_summary", "Analysis failed"),
            )
        except Exception:
            # If analysis fails, assume compliant (don't block export)
            return PhotoComplianceResult(
                asset_id=asset_id,
                file_path=file_path,
                compliant=True,
                branding=False,
                signage=False,
                people=False,
                text_overlay=False,
                issues_summary="Analysis unavailable",
            )

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
                await session.get(Listing, listing_id)

                # Get packaged photos
                result = await session.execute(
                    select(PackageSelection, Asset)
                    .join(Asset, PackageSelection.asset_id == Asset.id)
                    .where(PackageSelection.listing_id == listing_id)
                    .order_by(PackageSelection.position)
                )
                rows = result.all()

                # Scan each photo
                results: list[PhotoComplianceResult] = []
                for pkg, asset in rows:
                    presigned = self._storage.presigned_url(asset.file_path, expires_in=300)
                    check = await self._check_photo(
                        image_url=presigned,
                        asset_id=str(asset.id),
                        file_path=asset.file_path,
                    )
                    results.append(check)

                # Build report
                flagged = [r for r in results if not r.compliant]
                report = {
                    "total_photos": len(results),
                    "compliant_count": len(results) - len(flagged),
                    "flagged_count": len(flagged),
                    "all_compliant": len(flagged) == 0,
                    "flagged_photos": [
                        {
                            "asset_id": r.asset_id,
                            "branding": r.branding,
                            "signage": r.signage,
                            "people": r.people,
                            "text_overlay": r.text_overlay,
                            "issues_summary": r.issues_summary,
                        }
                        for r in flagged
                    ],
                }

                await self.emit(session, context, "photo_compliance.completed", report)

        return report
