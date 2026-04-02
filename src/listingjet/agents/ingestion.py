import io
import logging
import uuid

from PIL import Image
from sqlalchemy import select

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.services.events import emit_event
from listingjet.services.storage import get_storage

from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

PROXY_MAX_DIMENSION = 1024
PROXY_JPEG_QUALITY = 80
PROXY_TIMEOUT_SECONDS = 30


def _generate_proxy_bytes(original_bytes: bytes) -> bytes:
    """Resize image to 1024px longest edge, return JPEG bytes."""
    img = Image.open(io.BytesIO(original_bytes))
    img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > PROXY_MAX_DIMENSION:
        if w >= h:
            new_w = PROXY_MAX_DIMENSION
            new_h = int(h * (PROXY_MAX_DIMENSION / w))
        else:
            new_h = PROXY_MAX_DIMENSION
            new_w = int(w * (PROXY_MAX_DIMENSION / h))
        img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=PROXY_JPEG_QUALITY)
    return buf.getvalue()


class IngestionAgent(BaseAgent):
    agent_name = "ingestion"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)
        storage = get_storage()

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
                proxy_count = 0

                for asset in assets:
                    if asset.file_hash in seen_hashes:
                        asset.state = "duplicate"
                        duplicates.append(asset)
                    else:
                        seen_hashes.add(asset.file_hash)
                        asset.state = "ingested"
                        ingested.append(asset)

                        # Generate proxy image for AI analysis
                        proxy_key = f"listings/{listing_id}/proxies/{asset.id}.jpg"
                        try:
                            logger.info(
                                "Generating proxy for asset %s (file=%s)",
                                asset.id, asset.file_path,
                            )
                            original_bytes = storage.download(asset.file_path)
                            proxy_bytes = _generate_proxy_bytes(original_bytes)
                            storage.upload(
                                key=proxy_key,
                                data=proxy_bytes,
                                content_type="image/jpeg",
                            )
                            asset.proxy_path = proxy_key
                            proxy_count += 1
                            logger.info(
                                "Proxy generated for asset %s: %s (%d KB → %d KB)",
                                asset.id, proxy_key,
                                len(original_bytes) // 1024,
                                len(proxy_bytes) // 1024,
                            )
                        except Exception:
                            logger.exception(
                                "Failed to generate proxy for asset %s, "
                                "vision agents will fall back to full-res",
                                asset.id,
                            )

                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.ANALYZING

                await emit_event(
                    session=session,
                    event_type="ingestion.completed",
                    payload={
                        "ingested_count": len(ingested),
                        "duplicate_count": len(duplicates),
                        "proxy_count": proxy_count,
                    },
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

        return {
            "ingested_count": len(ingested),
            "duplicate_count": len(duplicates),
            "proxy_count": proxy_count,
        }
