import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.social_content import SocialContent
from listingjet.models.vision_result import VisionResult
from listingjet.services.storage import StorageService

from .base import AgentContext, BaseAgent

# MLS photo dimension profiles (max long-side px, JPEG quality)
MLS_PROFILES: dict[str, dict] = {
    "default":      {"max_px": 2048, "quality": 85},
    "reso":         {"max_px": 2048, "quality": 85},
    "bright_mls":   {"max_px": 2048, "quality": 90},
    "crmls":        {"max_px": 1024, "quality": 85},
    "mred":         {"max_px": 1024, "quality": 85},
    "fmls":         {"max_px": 800,  "quality": 80},
}

MLSProfile = Literal["default", "reso", "bright_mls", "crmls", "mred", "fmls"]


def _resize_photo(photo_bytes: bytes, profile: str = "default") -> bytes:
    """Resize photo to MLS profile dimensions, JPEG quality, strip EXIF. Falls back to original."""
    try:
        from PIL import Image

        spec = MLS_PROFILES.get(profile, MLS_PROFILES["default"])
        max_dim = spec["max_px"]
        quality = spec["quality"]

        img = Image.open(io.BytesIO(photo_bytes))
        img = img.convert("RGB")
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
    except Exception:
        return photo_bytes


def _build_metadata_csv(photos: list[dict]) -> bytes:
    """Build CSV with columns: filename, position, room_label, quality_score, caption, hero."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["filename", "position", "room_label", "quality_score", "caption", "hero"])
    writer.writeheader()
    for p in photos:
        writer.writerow(p)
    return buf.getvalue().encode("utf-8")


def _build_manifest(listing_id: str, photo_count: int, mode: str, includes_social: bool) -> bytes:
    """Build JSON manifest."""
    manifest = {
        "listing_id": listing_id,
        "photo_count": photo_count,
        "mode": mode,
        "includes_social": includes_social,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(manifest, indent=2).encode("utf-8")


class MLSExportAgent(BaseAgent):
    agent_name = "mls_export"

    def __init__(
        self,
        storage_service=None,
        session_factory=None,
        content_result=None,
        flyer_s3_key=None,
        mls_profile: str = "default",
    ):
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal
        self._content_result = content_result or {}
        self._flyer_s3_key = flyer_s3_key
        self._mls_profile = mls_profile

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
                # 1. Set listing state to EXPORTING
                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.EXPORTING

                # 2. Load PackageSelection + Asset + VisionResult rows
                result = await session.execute(
                    select(PackageSelection, Asset, VisionResult)
                    .join(Asset, PackageSelection.asset_id == Asset.id)
                    .outerjoin(
                        VisionResult,
                        (VisionResult.asset_id == Asset.id) & (VisionResult.tier == 1),
                    )
                    .where(PackageSelection.listing_id == listing_id)
                    .order_by(PackageSelection.position)
                )
                rows = result.all()

                # 3. Load SocialContent rows
                social_result = await session.execute(
                    select(SocialContent).where(SocialContent.listing_id == listing_id)
                )
                social_rows = social_result.scalars().all()

                # 4. Download and resize photos
                photos_meta = []
                photo_files = []  # (filename, bytes)
                for pkg, asset, vision in rows:
                    room_label = vision.room_label if vision else "unknown"
                    safe_label = room_label.replace(" ", "_").lower()
                    filename = f"{pkg.position:02d}_{safe_label}_{str(listing_id)[:8]}.jpg"

                    try:
                        raw = self._storage.download(asset.file_path)
                        resized = _resize_photo(raw, self._mls_profile)
                    except Exception:
                        continue  # skip failed photos

                    photo_files.append((filename, resized))
                    photos_meta.append({
                        "filename": filename,
                        "position": pkg.position,
                        "room_label": room_label,
                        "quality_score": vision.quality_score if vision else None,
                        "caption": vision.hero_explanation if vision else "",
                        "hero": pkg.position == 0,
                    })

                photo_count = len(photo_files)
                has_social = len(social_rows) > 0

                # 5. Build MLS bundle ZIP
                mls_zip_buf = io.BytesIO()
                with zipfile.ZipFile(mls_zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fname, fbytes in photo_files:
                        zf.writestr(fname, fbytes)
                    zf.writestr("metadata.csv", _build_metadata_csv(photos_meta))
                    zf.writestr(
                        "description_mls.txt",
                        self._content_result.get("mls_safe", ""),
                    )
                    zf.writestr(
                        "manifest.json",
                        _build_manifest(str(listing_id), photo_count, "mls", False),
                    )
                mls_zip_bytes = mls_zip_buf.getvalue()

                # 6. Build Marketing bundle ZIP
                mkt_zip_buf = io.BytesIO()
                with zipfile.ZipFile(mkt_zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Include everything from MLS
                    for fname, fbytes in photo_files:
                        zf.writestr(fname, fbytes)
                    zf.writestr("metadata.csv", _build_metadata_csv(photos_meta))
                    zf.writestr(
                        "description_mls.txt",
                        self._content_result.get("mls_safe", ""),
                    )
                    # Marketing extras
                    zf.writestr(
                        "description.txt",
                        self._content_result.get("marketing", ""),
                    )
                    if self._flyer_s3_key:
                        try:
                            flyer_bytes = self._storage.download(self._flyer_s3_key)
                            zf.writestr("flyer.pdf", flyer_bytes)
                        except Exception:
                            pass
                    if has_social:
                        social_data = [
                            {
                                "platform": sc.platform,
                                "caption": sc.caption,
                                "hashtags": sc.hashtags,
                                "cta": sc.cta,
                            }
                            for sc in social_rows
                        ]
                        zf.writestr("social_posts.json", json.dumps(social_data, indent=2))
                    zf.writestr(
                        "manifest.json",
                        _build_manifest(str(listing_id), photo_count, "marketing", has_social),
                    )
                mkt_zip_bytes = mkt_zip_buf.getvalue()

                # 7. Upload both ZIPs to S3
                mls_key = f"listings/{listing_id}/{listing_id}_mls.zip"
                mkt_key = f"listings/{listing_id}/{listing_id}_marketing.zip"
                self._storage.upload(key=mls_key, data=mls_zip_bytes, content_type="application/zip")
                self._storage.upload(key=mkt_key, data=mkt_zip_bytes, content_type="application/zip")

                # 8. Update listing paths
                listing.mls_bundle_path = mls_key
                listing.marketing_bundle_path = mkt_key

                # 9. Emit event
                await self.emit(session, context, "mls_export.completed", {
                    "mls_bundle_path": mls_key,
                    "marketing_bundle_path": mkt_key,
                    "photo_count": photo_count,
                })

        # 10. Return result
        return {
            "mls_bundle_path": mls_key,
            "marketing_bundle_path": mkt_key,
            "photo_count": photo_count,
        }
