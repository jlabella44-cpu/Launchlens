#!/usr/bin/env python3
"""Create a tenant, admin user, and one listing with 12 generated photos, then
enqueue the pipeline. For local runs with USE_MOCK_PROVIDERS=true.

Usage: .venv/Scripts/python.exe scripts/seed_sample_listing.py
Prints the listing id, the login email/password, and the job list.
"""
import asyncio
import io
import uuid
from datetime import datetime, timezone

from PIL import Image, ImageDraw

from listingjet.database import AsyncSessionLocal
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.pipeline.runner import enqueue_pipeline
from listingjet.services.auth import hash_password
from listingjet.services.storage import get_storage

ROOMS = ["exterior", "exterior", "living_room", "kitchen", "kitchen", "dining_room",
         "bedroom", "bedroom", "bedroom", "bathroom", "bathroom", "backyard"]


def _photo(label: str, i: int) -> bytes:
    img = Image.new("RGB", (1600, 1067), (40 + i * 15, 90, 160 - i * 10))
    ImageDraw.Draw(img).text((40, 40), f"{label} #{i}", fill="white")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


async def main() -> None:
    storage = get_storage()
    async with AsyncSessionLocal() as db:
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Seed Realty",
            plan="starter",
            plan_tier="starter",
            billing_model="legacy",
        )
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email=f"seed-{uuid.uuid4().hex[:6]}@example.com",
            password_hash=hash_password("SeedPass1!"),
            role=UserRole.ADMIN,
            name="Seed Admin",
            ai_consent_at=datetime.now(timezone.utc),
            ai_consent_version="v1",
        )
        listing = Listing(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            address={"street": "123 Sample St", "city": "Austin", "state": "TX", "zip": "78701"},
            metadata_={"beds": 3, "baths": 2, "sqft": 1850, "price": 525000},
            state=ListingState.UPLOADING,
        )
        db.add_all([tenant, user, listing])
        await db.flush()
        for i, room in enumerate(ROOMS):
            data = _photo(room, i)
            key = f"listings/{listing.id}/uploads/{uuid.uuid4()}/{room}_{i}.jpg"
            try:
                storage.upload_bytes(data, key=key, content_type="image/jpeg")
            except Exception as exc:  # noqa: BLE001 — local seed convenience only
                print(f"WARNING: storage upload failed for {key}: {exc}")
            db.add(Asset(
                tenant_id=tenant.id,
                listing_id=listing.id,
                file_path=key,
                file_hash=f"seed{i:02d}",
                state="uploaded",
            ))
        jobs = await enqueue_pipeline(db, listing, billing_model="legacy", enabled_addons=[])
        await db.commit()
    print(f"listing_id={listing.id}\nlogin={user.email} / SeedPass1!\njobs={[j.step for j in jobs]}")


if __name__ == "__main__":
    asyncio.run(main())
