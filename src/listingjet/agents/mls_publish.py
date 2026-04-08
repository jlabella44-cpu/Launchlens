"""
MLS Publish Agent — submits a listing to the MLS via RESO Web API.

Flow:
1. Load listing + package photos + MLS-safe description
2. Load the tenant's active MLS connection
3. Map listing data → RESO Data Dictionary payload
4. Submit property record via POST /Property
5. Upload curated photos via POST /Media
6. Update MLSPublishRecord with result
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.mls_connection import MLSConnection
from listingjet.models.mls_publish_record import MLSPublishRecord, PublishStatus
from listingjet.models.package_selection import PackageSelection
from listingjet.models.vision_result import VisionResult
from listingjet.services.reso_adapter import (
    RESOAdapter,
    RESOConnectionConfig,
    build_media_payload,
    map_listing_to_reso,
)
from listingjet.services.storage import StorageService

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)


class MLSPublishAgent(BaseAgent):
    agent_name = "mls_publish"

    def __init__(
        self,
        storage_service=None,
        session_factory=None,
        reso_adapter=None,
        content_result=None,
    ):
        self._storage = storage_service or StorageService()
        self._session_factory = session_factory or AsyncSessionLocal
        self._reso_adapter = reso_adapter  # injectable for testing
        self._content_result = content_result or {}

    async def execute(self, context: AgentContext) -> dict:
        async with self.session_scope(context) as (session, listing_id, tenant_id):
            # 1. Load listing
            listing = await session.get(Listing, listing_id)
            if not listing:
                raise RuntimeError(f"Listing {listing_id} not found")

            # 2. Load the active MLS connection for this tenant
            conn_result = await session.execute(
                select(MLSConnection)
                .where(
                    MLSConnection.tenant_id == tenant_id,
                    MLSConnection.is_active.is_(True),
                )
                .limit(1)
            )
            mls_conn = conn_result.scalar_one_or_none()
            if not mls_conn:
                raise RuntimeError("No active MLS connection configured for this tenant")

            # 3. Find or create the publish record
            existing = await session.execute(
                select(MLSPublishRecord).where(
                    MLSPublishRecord.listing_id == listing_id,
                    MLSPublishRecord.connection_id == mls_conn.id,
                    MLSPublishRecord.status.notin_(
                        [
                            PublishStatus.CONFIRMED,
                            PublishStatus.FAILED,
                        ]
                    ),
                )
            )
            publish_record = existing.scalar_one_or_none()
            if not publish_record:
                publish_record = MLSPublishRecord(
                    tenant_id=tenant_id,
                    listing_id=listing_id,
                    connection_id=mls_conn.id,
                    status=PublishStatus.PENDING,
                )
                session.add(publish_record)
                await session.flush()

            # 4. Set listing state to PUBLISHING
            listing.state = ListingState.PUBLISHING

            # 5. Build RESO adapter
            adapter = self._reso_adapter or RESOAdapter(
                config=RESOConnectionConfig(
                    base_url=mls_conn.reso_api_url,
                    oauth_token_url=mls_conn.oauth_token_url,
                    client_id=mls_conn.client_id,
                    client_secret=mls_conn.client_secret_encrypted,
                    bearer_token=mls_conn.bearer_token_encrypted,
                )
            )

            # 6. Map listing → RESO payload
            # Include MLS-safe description if available
            meta = dict(listing.metadata_ or {})
            if self._content_result.get("mls_safe"):
                meta["description"] = self._content_result["mls_safe"]

            reso_payload = map_listing_to_reso(listing.address, meta)

            # Board-specific overrides from connection config
            overrides = mls_conn.config.get("field_overrides", {})
            reso_payload.update(overrides)

            # 7. Submit property
            publish_record.status = PublishStatus.SUBMITTING_PROPERTY
            await session.flush()

            audit_entries = []
            try:
                prop_result = await adapter.submit_property(reso_payload)
                listing_key = prop_result.get("ListingKey", "")
                publish_record.reso_listing_key = listing_key
                publish_record.reso_property_id = prop_result.get("ListingId", listing_key)
                publish_record.submitted_at = datetime.now(timezone.utc)

                audit_entries.append(
                    {
                        "step": "submit_property",
                        "status": "success",
                        "listing_key": listing_key,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception as exc:
                publish_record.status = PublishStatus.FAILED
                publish_record.error_message = str(exc)[:2000]
                publish_record.error_code = "PROPERTY_SUBMIT_FAILED"
                audit_entries.append(
                    {
                        "step": "submit_property",
                        "status": "failed",
                        "error": str(exc)[:500],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                publish_record.audit_log = audit_entries
                listing.state = ListingState.DELIVERED  # revert

                await self.emit(
                    session,
                    context,
                    "mls_publish.failed",
                    {
                        "error": str(exc)[:500],
                        "step": "submit_property",
                    },
                )
                raise

            # 8. Load curated photos and upload as RESO Media
            publish_record.status = PublishStatus.SUBMITTING_MEDIA
            await session.flush()

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

            media_payloads = []
            for pkg, asset, vision in rows:
                # Generate presigned URL for the photo (RESO server will fetch it)
                photo_url = self._storage.presigned_url(asset.file_path, expires_in=3600)
                room_label = vision.room_label if vision else ""
                caption = vision.hero_explanation if vision else ""

                media_payloads.append(
                    build_media_payload(
                        photo_url=photo_url,
                        position=pkg.position,
                        room_label=room_label,
                        caption=caption,
                        is_hero=(pkg.position == 0),
                    )
                )

            publish_record.photos_submitted = len(media_payloads)

            try:
                media_result = await adapter.submit_media(listing_key, media_payloads)
                publish_record.photos_accepted = media_result["accepted"]

                audit_entries.append(
                    {
                        "step": "submit_media",
                        "status": "success",
                        "accepted": media_result["accepted"],
                        "rejected": media_result["rejected"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception as exc:
                publish_record.status = PublishStatus.FAILED
                publish_record.error_message = str(exc)[:2000]
                publish_record.error_code = "MEDIA_SUBMIT_FAILED"
                audit_entries.append(
                    {
                        "step": "submit_media",
                        "status": "failed",
                        "error": str(exc)[:500],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                publish_record.audit_log = audit_entries
                listing.state = ListingState.DELIVERED  # revert

                await self.emit(
                    session,
                    context,
                    "mls_publish.failed",
                    {
                        "error": str(exc)[:500],
                        "step": "submit_media",
                    },
                )
                raise

            # 9. Mark as submitted
            publish_record.status = PublishStatus.SUBMITTED
            publish_record.audit_log = audit_entries
            listing.state = ListingState.DELIVERED  # listing stays DELIVERED

            await self.emit(
                session,
                context,
                "mls_publish.completed",
                {
                    "listing_key": listing_key,
                    "photos_accepted": media_result["accepted"],
                    "photos_rejected": media_result["rejected"],
                },
            )

        return {
            "status": "submitted",
            "reso_listing_key": listing_key,
            "photos_submitted": len(media_payloads),
            "photos_accepted": media_result["accepted"],
        }
