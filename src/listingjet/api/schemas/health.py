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


# -- IDX Feed Config Schemas --

class IdxFeedConfigCreate(BaseModel):
    name: str = Field(..., max_length=255)
    base_url: str = Field(..., max_length=500)
    api_key: str = Field(..., max_length=500)
    board_id: str | None = Field(None, max_length=100)
    poll_interval_minutes: int = Field(60, ge=15, le=1440)


class IdxFeedConfigUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    base_url: str | None = Field(None, max_length=500)
    api_key: str | None = Field(None, max_length=500)
    board_id: str | None = Field(None, max_length=100)
    poll_interval_minutes: int | None = Field(None, ge=15, le=1440)
    status: str | None = Field(None, pattern="^(active|disabled)$")


class IdxFeedConfigResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_url: str
    board_id: str | None
    poll_interval_minutes: int
    last_polled_at: datetime | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


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
