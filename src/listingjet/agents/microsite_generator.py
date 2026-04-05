"""MicrositeGeneratorAgent — generates single-property landing pages.

Produces a standalone HTML page with hero photo, gallery, property details,
video tour embed, and agent contact. Uploads to S3 for CDN delivery.
Also generates a QR code linking to the microsite.
"""
import io
import logging
import uuid

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.listing import Listing
from listingjet.models.listing_microsite import ListingMicrosite
from listingjet.models.package_selection import PackageSelection
from listingjet.models.property_data import PropertyData
from listingjet.models.video_asset import VideoAsset
from listingjet.services.storage import StorageService

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

_MICROSITE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Helvetica Neue', system-ui, -apple-system, sans-serif; color: #1e293b; }}
.hero {{ position: relative; height: 70vh; min-height: 400px; background: #0b1120; overflow: hidden; }}
.hero img {{ width: 100%; height: 100%; object-fit: cover; opacity: 0.7; }}
.hero-overlay {{ position: absolute; bottom: 0; left: 0; right: 0; padding: 40px; background: linear-gradient(transparent, rgba(0,0,0,0.8)); color: white; }}
.hero-overlay h1 {{ font-size: 2.5rem; font-weight: 800; margin-bottom: 8px; }}
.hero-overlay .stats {{ display: flex; gap: 24px; font-size: 1.1rem; opacity: 0.9; }}
.container {{ max-width: 1100px; margin: 0 auto; padding: 40px 24px; }}
h2 {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 16px; color: {primary_color}; }}
.gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; margin-bottom: 40px; }}
.gallery img {{ width: 100%; height: 200px; object-fit: cover; border-radius: 8px; cursor: pointer; transition: transform 0.2s; }}
.gallery img:hover {{ transform: scale(1.03); }}
.details {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 40px; }}
.detail-card {{ background: #f8fafc; border-radius: 12px; padding: 20px; }}
.detail-card .label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 4px; }}
.detail-card .value {{ font-size: 1.25rem; font-weight: 700; }}
.video-section {{ margin-bottom: 40px; }}
.video-section video {{ width: 100%; border-radius: 12px; }}
.scores {{ display: flex; gap: 24px; margin-bottom: 40px; flex-wrap: wrap; }}
.score {{ background: #f8fafc; border-radius: 12px; padding: 20px 28px; text-align: center; }}
.score .num {{ font-size: 2rem; font-weight: 800; color: {primary_color}; }}
.score .label {{ font-size: 0.75rem; text-transform: uppercase; color: #64748b; }}
.agent {{ background: {primary_color}; color: white; border-radius: 16px; padding: 32px; display: flex; align-items: center; gap: 24px; margin-top: 40px; }}
.agent .info h3 {{ font-size: 1.25rem; margin-bottom: 4px; }}
.agent .info p {{ opacity: 0.8; font-size: 0.9rem; }}
.agent a {{ color: white; text-decoration: underline; }}
.footer {{ text-align: center; padding: 24px; font-size: 0.75rem; color: #94a3b8; }}
@media (max-width: 640px) {{
    .hero-overlay h1 {{ font-size: 1.5rem; }}
    .hero-overlay .stats {{ flex-direction: column; gap: 4px; }}
    .agent {{ flex-direction: column; text-align: center; }}
}}
</style>
</head>
<body>

<section class="hero">
<img src="{hero_image_url}" alt="{title}">
<div class="hero-overlay">
<h1>{street}</h1>
<p style="margin-bottom:8px">{city_state_zip}</p>
<div class="stats">
{stats_html}
</div>
</div>
</section>

<div class="container">

{price_section}

<h2>Photo Gallery</h2>
<div class="gallery">
{gallery_html}
</div>

{details_section}

{scores_section}

{video_section}

<div class="agent">
<div class="info">
<h3>{agent_name}</h3>
<p>{brokerage_name}</p>
<p><a href="mailto:{agent_email}">Contact Agent</a></p>
</div>
</div>

</div>

<div class="footer">
Powered by ListingJet &mdash; AI-Powered Real Estate Marketing
</div>

</body>
</html>
"""


class MicrositeGeneratorAgent(BaseAgent):
    agent_name = "microsite_generator"

    def __init__(self, storage_service=None, session_factory=None):
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            listing = await session.get(Listing, listing_id)
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            address = listing.address or {}
            meta = listing.metadata_ or {}

            # Load property data
            prop = (await session.execute(
                select(PropertyData).where(PropertyData.listing_id == listing_id)
            )).scalar_one_or_none()

            # Load brand kit
            brand_kit = (await session.execute(
                select(BrandKit).where(BrandKit.tenant_id == tenant_id).limit(1)
            )).scalar_one_or_none()

            # Load assets (ordered by package selection if available)
            pkg_results = (await session.execute(
                select(PackageSelection, Asset)
                .join(Asset, PackageSelection.asset_id == Asset.id)
                .where(PackageSelection.listing_id == listing_id)
                .order_by(PackageSelection.position)
                .limit(15)
            )).all()

            if pkg_results:
                assets = [asset for _, asset in pkg_results]
            else:
                assets = list((await session.execute(
                    select(Asset).where(
                        Asset.listing_id == listing_id,
                        Asset.state != "staged",
                    ).limit(15)
                )).scalars().all())

            # Load video
            video = (await session.execute(
                select(VideoAsset).where(
                    VideoAsset.listing_id == listing_id,
                    VideoAsset.status == "ready",
                ).order_by(VideoAsset.created_at.desc()).limit(1)
            )).scalar_one_or_none()

            # Build data
            street = address.get("street", "Property")
            city = address.get("city", "")
            state = address.get("state", "")
            zip_code = address.get("zip", "")
            city_state_zip = f"{city}, {state} {zip_code}".strip(", ")
            title = f"{street}, {city_state_zip}" if city_state_zip else street

            beds = prop.beds if prop else meta.get("beds")
            baths = prop.baths if prop else meta.get("baths")
            sqft = prop.sqft if prop else meta.get("sqft")
            price = meta.get("price")
            year_built = prop.year_built if prop else meta.get("year_built")

            primary_color = brand_kit.primary_color if brand_kit else "#F97316"
            agent_name = brand_kit.agent_name if brand_kit else "Agent"
            brokerage_name = brand_kit.brokerage_name if brand_kit else ""
            agent_email = "contact@listingjet.ai"

            # Stats line
            stats = []
            if beds:
                stats.append(f"<span>{beds} Beds</span>")
            if baths:
                stats.append(f"<span>{baths} Baths</span>")
            if sqft:
                stats.append(f"<span>{sqft:,} Sqft</span>")
            if year_built:
                stats.append(f"<span>Built {year_built}</span>")

            # Price section
            price_section = ""
            if price:
                price_section = f'<h2 style="font-size:2rem;margin-bottom:24px">${price:,}</h2>'

            # Gallery
            gallery_items = []
            hero_url = ""
            for i, asset in enumerate(assets):
                url = self._storage.presigned_url(asset.file_path, expires_in=604800)  # 7 days
                if i == 0:
                    hero_url = url
                gallery_items.append(f'<img src="{url}" alt="Property photo {i + 1}" loading="lazy">')
            gallery_html = "\n".join(gallery_items)

            # Details section
            details = []
            if beds:
                details.append(("Bedrooms", str(beds)))
            if baths:
                details.append(("Bathrooms", str(baths)))
            if sqft:
                details.append(("Square Feet", f"{sqft:,}"))
            if year_built:
                details.append(("Year Built", str(year_built)))
            if prop and prop.property_type:
                details.append(("Property Type", prop.property_type.replace("_", " ").title()))
            if prop and prop.garage_spaces:
                details.append(("Garage", f"{prop.garage_spaces} car"))
            if prop and prop.hoa_monthly:
                details.append(("HOA", f"${prop.hoa_monthly:,.0f}/mo"))

            details_html = ""
            if details:
                cards = "\n".join(
                    f'<div class="detail-card"><div class="label">{label}</div><div class="value">{val}</div></div>'
                    for label, val in details
                )
                details_html = f"<h2>Property Details</h2>\n<div class='details'>\n{cards}\n</div>"

            # Scores
            scores_html = ""
            if prop:
                score_items = []
                if prop.walk_score:
                    score_items.append(f'<div class="score"><div class="num">{prop.walk_score}</div><div class="label">Walk Score</div></div>')
                if prop.transit_score:
                    score_items.append(f'<div class="score"><div class="num">{prop.transit_score}</div><div class="label">Transit Score</div></div>')
                if prop.bike_score:
                    score_items.append(f'<div class="score"><div class="num">{prop.bike_score}</div><div class="label">Bike Score</div></div>')
                if score_items:
                    scores_html = f"<h2>Neighborhood</h2>\n<div class='scores'>\n{''.join(score_items)}\n</div>"

            # Video
            video_html = ""
            if video and video.s3_key:
                video_url = self._storage.presigned_url(video.s3_key, expires_in=604800)
                video_html = f'''<div class="video-section">
<h2>Video Tour</h2>
<video controls poster="{hero_url}"><source src="{video_url}" type="video/mp4"></video>
</div>'''

            description = meta.get("description", "")

            # Render HTML
            html = _MICROSITE_HTML.format(
                title=title,
                description=description[:200] if description else f"{beds or ''}bd/{baths or ''}ba property at {street}",
                primary_color=primary_color,
                hero_image_url=hero_url or "",
                street=street,
                city_state_zip=city_state_zip,
                stats_html="\n".join(stats),
                price_section=price_section,
                gallery_html=gallery_html,
                details_section=details_html,
                scores_section=scores_html,
                video_section=video_html,
                agent_name=agent_name,
                brokerage_name=brokerage_name,
                agent_email=agent_email,
            )

            # Upload to S3
            s3_key = f"microsites/{listing_id}/index.html"
            self._storage.upload(s3_key, html.encode("utf-8"), content_type="text/html")

            microsite_url = self._storage.presigned_url(s3_key, expires_in=604800)

            # Generate QR code
            qr_s3_key = None
            try:
                qr_s3_key = await self._generate_qr(listing_id, microsite_url)
            except Exception:
                logger.warning("qr_code_generation_failed listing=%s", listing_id, exc_info=True)

            # Save/update microsite record
            existing = (await session.execute(
                select(ListingMicrosite).where(ListingMicrosite.listing_id == listing_id)
            )).scalar_one_or_none()

            if existing:
                existing.s3_key = s3_key
                existing.qr_code_s3_key = qr_s3_key
                existing.microsite_url = microsite_url
                existing.status = "ready"
            else:
                microsite = ListingMicrosite(
                    tenant_id=tenant_id,
                    listing_id=listing_id,
                    s3_key=s3_key,
                    qr_code_s3_key=qr_s3_key,
                    microsite_url=microsite_url,
                    status="ready",
                )
                session.add(microsite)

            await self.emit(session, context, "microsite.completed", {
                "listing_id": str(listing_id),
                "s3_key": s3_key,
                "has_qr": qr_s3_key is not None,
            })

        return {"s3_key": s3_key, "microsite_url": microsite_url, "qr_code_s3_key": qr_s3_key}

    async def _generate_qr(self, listing_id: uuid.UUID, url: str) -> str:
        """Generate a QR code PNG and upload to S3."""
        try:
            import qrcode
        except ImportError:
            logger.warning("qrcode package not installed — skipping QR generation")
            raise

        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        s3_key = f"microsites/{listing_id}/qr-code.png"
        self._storage.upload(s3_key, buffer.read(), content_type="image/png")
        return s3_key
