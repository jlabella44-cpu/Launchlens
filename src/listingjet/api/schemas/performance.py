"""Pydantic schemas for performance intelligence endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class RoomCorrelation(BaseModel):
    room: str
    boost: float
    avg_dom: float | None = None
    sample_count: int = 0


class HeroInsight(BaseModel):
    room: str
    boost: float
    avg_dom: float | None = None
    avg_price_ratio: float | None = None
    sample_count: int = 0


class QualityImpact(BaseModel):
    bucket: str
    boost: float
    avg_dom: float | None = None
    sample_count: int = 0


class PerformanceInsightsResponse(BaseModel):
    summary: str
    outcomes_count: int
    avg_dom: float | None = None
    avg_price_ratio: float | None = None
    grade_distribution: dict[str, int] = {}
    top_rooms: list[RoomCorrelation] = []
    hero_insights: list[HeroInsight] = []
    quality_impact: list[QualityImpact] = []


class ListingOutcomeResponse(BaseModel):
    listing_id: uuid.UUID
    status: str
    list_price: float | None = None
    sale_price: float | None = None
    price_ratio: float | None = None
    days_on_market: int | None = None
    days_to_contract: int | None = None
    price_changes: int = 0
    total_photos_mls: int | None = None
    hero_room_label: str | None = None
    avg_photo_score: float | None = None
    outcome_grade: str | None = None
    idx_source: str | None = None
    first_seen_at: datetime | None = None
    closed_at: datetime | None = None

    model_config = {"from_attributes": True}


class OutcomeSummaryResponse(BaseModel):
    total_tracked: int
    total_closed: int
    total_pending: int
    total_active: int
    avg_dom: float | None = None
    avg_price_ratio: float | None = None
    grade_distribution: dict[str, int] = {}
    listings: list[ListingOutcomeResponse] = []
