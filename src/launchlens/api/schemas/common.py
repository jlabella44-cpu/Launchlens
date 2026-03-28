"""Shared Pydantic schemas used across multiple API modules."""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard wrapper for paginated list endpoints."""

    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
