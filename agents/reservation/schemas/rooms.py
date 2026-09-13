from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RoomSearchRequest(BaseModel):
    """Search filters for available rooms.

    Used by the `search_rooms` tool and the room search API route. Dates
    are validated here so bad input is rejected before it ever reaches the
    database query.
    """

    check_in_date: date
    check_out_date: date
    guests: int = Field(ge=1, le=20)
    room_type: Optional[str] = None
    max_price: Optional[Decimal] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_date_range(self) -> "RoomSearchRequest":
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date must be after check_in_date")
        if self.check_in_date < date.today():
            raise ValueError("check_in_date cannot be in the past")
        return self


class RoomOut(BaseModel):
    """A room as returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_number: str
    room_type: str
    description: Optional[str] = None
    capacity: int
    price_per_night: Decimal


class RoomSearchResult(BaseModel):
    """A room plus computed pricing for a specific search's date range."""

    room: RoomOut
    nights: int
    total_price: Decimal