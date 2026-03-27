import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None
    company_name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    tenant_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
