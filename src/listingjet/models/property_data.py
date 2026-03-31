import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UUID, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class PropertyData(Base):
    __tablename__ = "property_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    address_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    property_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="normal")
    api_source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    api_raw: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Physical attributes
    beds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baths: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    half_baths: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sqft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lot_sqft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    property_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    stories: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    garage_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_pool: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_basement: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    heating_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cooling_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    roof_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hoa_monthly: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Scores and amenities
    walk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transit_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bike_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nearby_amenities: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    school_ratings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    lifestyle_tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Verification
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    field_confidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    mismatches: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    scraped_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sources_checked: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
