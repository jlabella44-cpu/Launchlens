"""Email blast generation — AI-written email copy for a listing."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, get_db
from listingjet.models.listing import Listing
from listingjet.models.social_content import SocialContent
from listingjet.models.user import User
from listingjet.models.vision_result import VisionResult
from listingjet.providers import get_llm_provider
from listingjet.services.endpoint_rate_limit import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


class EmailBlastRequest(BaseModel):
    subject_hint: str = Field(default="", description="Optional subject line hint or tone")
    call_to_action_url: str = Field(default="", description="URL for the CTA button (e.g. microsite link)")
    agent_name: str = Field(default="", description="Agent name to include in sign-off")
    agent_phone: str = Field(default="", description="Agent phone for the footer")


class EmailBlastResponse(BaseModel):
    subject: str
    html: str
    plain_text: str
    listing_id: str


@router.post("/{listing_id}/email-blast", response_model=EmailBlastResponse)
async def generate_email_blast(
    listing_id: uuid.UUID,
    body: EmailBlastRequest,
    _rl=Depends(rate_limit(5, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI-written email blast for a listing."""
    listing = (await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == current_user.tenant_id,
        )
    )).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Gather listing context
    address = listing.address or {}
    street = address.get("street", "this property")
    city = address.get("city", "")
    state = address.get("state", "")
    location = f"{city}, {state}".strip(", ") or "a prime location"

    details = listing.property_details or {}
    beds = details.get("bedrooms", "")
    baths = details.get("bathrooms", "")
    sqft = details.get("square_feet", "")
    price = details.get("list_price", "")

    # Grab marketing description from social content or package
    social = (await db.execute(
        select(SocialContent).where(
            SocialContent.listing_id == listing_id,
            SocialContent.platform == "email",
        )
    )).scalar_one_or_none()

    marketing_desc = (social.caption if social else None) or listing.mls_description or ""

    # Top vision result for feature highlights
    hero_vision = (await db.execute(
        select(VisionResult).where(
            VisionResult.listing_id == listing_id,
            VisionResult.tier == 1,
        ).order_by(VisionResult.quality_score.desc()).limit(1)
    )).scalar_one_or_none()
    hero_room = hero_vision.room_label if hero_vision else ""

    llm = get_llm_provider(agent="email_blast")

    property_summary = (
        f"Property: {street}, {location}\n"
        f"Beds: {beds}, Baths: {baths}, Sqft: {sqft}, Price: {price}\n"
        f"Standout feature: {hero_room}\n"
        f"Description: {marketing_desc}"
    )
    subject_hint = f"Subject hint: {body.subject_hint}" if body.subject_hint else ""
    cta_url = body.call_to_action_url or "#"

    prompt = f"""Write a compelling real estate email blast for the following property.
Return JSON with keys: subject (string), body_html (string with inline-CSS HTML email body), body_text (plain-text version).

{property_summary}
{subject_hint}

Requirements:
- Subject line: punchy, 8-12 words, no emoji
- HTML: mobile-friendly, inline CSS, single column, include a CTA button linking to {cta_url}
- Highlight the best features without generic filler phrases
- Sign-off with: {body.agent_name or "Your Agent"} | {body.agent_phone or ""}
- Keep the plain-text version under 200 words

Respond ONLY with valid JSON, no markdown fences."""

    try:
        raw = await llm.complete(prompt)
    except Exception:
        logger.exception("LLM error generating email blast for listing %s", listing_id)
        raise HTTPException(status_code=502, detail="Email generation failed — try again")

    # Parse LLM JSON response
    import json as _json
    try:
        parsed = _json.loads(raw)
        subject = parsed.get("subject", f"Just Listed: {street}")
        body_html = parsed.get("body_html", "")
        body_text = parsed.get("body_text", "")
    except _json.JSONDecodeError:
        # Fallback: treat raw as plain text
        subject = f"Just Listed: {street}"
        body_html = f"<p>{raw}</p>"
        body_text = raw

    return EmailBlastResponse(
        subject=subject,
        html=body_html,
        plain_text=body_text,
        listing_id=str(listing_id),
    )
