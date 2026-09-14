from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents.reservation.schemas.hotels import HotelOut


class RoomSearchRequest(BaseModel):
    """Search filters for available rooms across the whole platform.

    Used by the `search_rooms` tool and the room search API route. Dates
    are validated here so bad input is rejected before it ever reaches the
    database query. `city` and `hotel_id` are both optional and
    independent: a guest can browse every hotel in a city, search within
    one specific hotel, or search the entire platform with no location
    filter at all.
    """

    check_in_date: date
    check_out_date: date
    guests: int = Field(ge=1, le=20)
    city: Optional[str] = None
    hotel_id: Optional[int] = None
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
    """A room as returned to clients, with its hotel embedded.

    The hotel is embedded (not just hotel_id) because in a multi-hotel
    platform, a room is meaningless on its own — "Room 101, $80/night" only
    makes sense alongside which hotel and which city it's in.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    hotel: HotelOut
    room_number: str
    room_type: str
    description: Optional[str] = None
    capacity: int
    price_per_night: Decimal


class RoomCreateRequest(BaseModel):
    """Admin-only: add a new room to a hotel's inventory.

    Guarded by a staff-role check at the API layer, not by anything in
    this schema — Pydantic validates shape, not who's allowed to submit it.
    """

    hotel_id: int
    room_number: str = Field(min_length=1, max_length=20)
    room_type: str = Field(min_length=1)
    description: Optional[str] = None
    capacity: int = Field(ge=1, le=20)
    price_per_night: Decimal = Field(gt=0)
    is_active: bool = True


class RoomSearchResult(BaseModel):
    """A room plus computed pricing for a specific search's date range."""

    room: RoomOut
    nights: int
    total_price: Decimal
