"""Standard error response models for OpenAPI documentation."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class ValidationErrorResponse(BaseModel):
    detail: list[dict]
