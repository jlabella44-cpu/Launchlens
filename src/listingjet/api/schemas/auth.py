import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None
    company_name: str
    plan_tier: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "agent@realty.com",
                    "password": "SecurePass1!",
                    "name": "Jane Smith",
                    "company_name": "Smith Realty",
                    "plan_tier": "active_agent",
                }
            ]
        }
    }

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "agent@realty.com", "password": "SecurePass1!"}]
        }
    }


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    tenant_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
