import uuid
from datetime import datetime

from pydantic import BaseModel


class DemoUploadRequest(BaseModel):
    file_paths: list[str]


class DemoUploadResponse(BaseModel):
    demo_id: uuid.UUID
    photo_count: int
    expires_at: datetime


class DemoViewResponse(BaseModel):
    demo_id: uuid.UUID
    address: dict
    state: str
    is_demo: bool
    photos: list[dict] = []
    locked_features: list[str] = ["description", "flyer", "social_posts", "export"]
