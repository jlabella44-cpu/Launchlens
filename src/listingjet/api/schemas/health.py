"""Pydantic schemas for listing health score and IDX feed config endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# -- Health Score Schemas --

class HealthSubScoreDetail(BaseModel):
    score: int
    weight: float
    details: dict

    model_config = {"from_attributes": True}


class HealthBreakdown(BaseModel):
    media_quality: HealthSubScoreDetail | None = None
    content_readiness: HealthSubScoreDetail | None = None
    pipeline_velocity: HealthSubScoreDetail | None = None
    syndication: HealthSubScoreDetail | None = None
    market_signal: HealthSubScoreDetail | None = None


class HealthTrendPoint(BaseModel):
    date: str
    overall: int
    media: int = 0
    content: int = 0
    velocity: int = 0
    syndication: int = 0
    market: int = 0


class ListingHealthResponse(BaseModel):
    listing_id: uuid.UUID
    overall_score: int
    breakdown: HealthBreakdown
    trend: list[HealthTrendPoint]
    calculated_at: datetime | None = None

    model_config = {"from_attributes": True}


class HealthSummaryListing(BaseModel):
    listing_id: uuid.UUID
    address: dict
    overall_score: int


class HealthSummaryResponse(BaseModel):
    average_score: float
    total_scored: int
    distribution: dict[str, int]  # "green": N, "yellow": N, "red": N
    top_listings: list[HealthSummaryListing]
    bottom_listings: list[HealthSummaryListing]


# -- Health Weights Schemas --

class HealthWeightsResponse(BaseModel):
    media: float
    content: float
    velocity: float
    syndication: float
    market: float


class HealthWeightsUpdate(BaseModel):
    media: float = Field(..., ge=0, le=1)
    content: float = Field(..., ge=0, le=1)
    velocity: float = Field(..., ge=0, le=1)
    syndication: float = Field(..., ge=0, le=1)
    market: float = Field(..., ge=0, le=1)
