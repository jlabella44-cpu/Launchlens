"""Pydantic schemas for Team API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    name: str | None
    email: str
    role: str
    created_at: datetime
    # Populated when the user has a pending invitation and has not yet set
    # a password. Frontend can show a "Pending" indicator.
    pending_invite: bool = False
    model_config = {"from_attributes": True}


class InviteTeamMemberRequest(BaseModel):
    email: str
    name: str | None = None
    role: str = "agent"


class InviteTeamMemberResponse(BaseModel):
    """Returned from POST /team/members after sending the invitation email."""
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    invite_expires_at: datetime


class InviteInfoResponse(BaseModel):
    """Public lookup of an invitation from its token — used by the accept page."""
    email: str
    tenant_name: str
    inviter_name: str | None
    expires_at: datetime


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)
    name: str | None = None


class UpdateRoleRequest(BaseModel):
    role: str
