from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class HotelOut(BaseModel):
    """A hotel as returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    city: str
    address: Optional[str] = None
    description: Optional[str] = None
    star_rating: Optional[int] = None


class HotelCreateRequest(BaseModel):
    """Admin-only: add a new hotel to the platform."""

    name: str = Field(min_length=1)
    city: str = Field(min_length=1)
    address: Optional[str] = None
    description: Optional[str] = None
    star_rating: Optional[int] = Field(default=None, ge=1, le=5)
