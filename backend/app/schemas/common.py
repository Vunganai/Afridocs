"""
Shared Pydantic schema primitives used across the API.
"""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class CamelModel(BaseModel):
    """Base model that serialises to camelCase for the frontend."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class PaginatedResponse(CamelModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool


class MessageResponse(CamelModel):
    message: str


class ErrorResponse(CamelModel):
    error: str
