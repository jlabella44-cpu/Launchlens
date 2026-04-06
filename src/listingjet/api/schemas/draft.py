"""Schemas for draft listing flow (staging tags + start pipeline)."""
from pydantic import BaseModel, Field


class StagingTagRequest(BaseModel):
    asset_ids: list[str] = Field(..., min_length=1, description="Asset UUIDs to tag for virtual staging")


class StagingTagResponse(BaseModel):
    tagged_count: int
    listing_id: str


class StartPipelineRequest(BaseModel):
    selected_addons: list[str] = Field(default_factory=list, description="Addon slugs to activate (or 'all_addons_bundle')")


class StartPipelineResponse(BaseModel):
    listing_id: str
    state: str
    credits_deducted: int
    workflow_id: str
