import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class BrandKitResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    font_primary: str | None = None
    agent_name: str | None = None
    brokerage_name: str | None = None
    raw_config: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class BrandKitUpsertRequest(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    font_primary: str | None = None
    agent_name: str | None = None
    brokerage_name: str | None = None
    raw_config: dict | None = None

    @field_validator("primary_color", "secondary_color")
    @classmethod
    def validate_hex_color(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v.startswith("#") or len(v) != 7:
                raise ValueError("Color must be a 7-character hex string (e.g. #2563EB)")
        return v
