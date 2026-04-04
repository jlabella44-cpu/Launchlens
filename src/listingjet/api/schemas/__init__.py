"""Shared API schema models."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str
