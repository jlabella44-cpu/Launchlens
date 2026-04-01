"""Pydantic schemas for Team API."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    name: str | None
    email: str
    role: str
    created_at: datetime
    model_config = {"from_attributes": True}


class InviteTeamMemberRequest(BaseModel):
    email: str
    name: str | None = None
    password: str
    role: str = "agent"


class UpdateRoleRequest(BaseModel):
    role: str
