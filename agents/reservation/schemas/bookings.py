from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents.reservation.schemas.rooms import RoomOut


class AvailabilityCheckRequest(BaseModel):
    room_id: int
    check_in_date: date
    check_out_date: date
    guests: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_date_range(self) -> "AvailabilityCheckRequest":
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date must be after check_in_date")
        return self


class AvailabilityCheckResponse(BaseModel):
    room_id: int
    is_available: bool
    reason: Optional[str] = None
    nights: int
    total_price: Optional[Decimal] = None


class CreateBookingRequest(BaseModel):
    """Booking creation payload.

    Deliberately has NO `user_id` field. The authenticated user's id must
    be read from the session (`get_current_user`) at the API layer and
    passed into the service separately — never accepted from the client.
    This mirrors a real vulnerability class already flagged elsewhere in
    this codebase (client-suppliable `role` on registration): never let a
    client tell the backend who it is or what it's allowed to do.
    """

    room_id: int
    check_in_date: date
    check_out_date: date
    guests: int = Field(ge=1)
    special_requests: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_date_range(self) -> "CreateBookingRequest":
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date must be after check_in_date")
        if self.check_in_date < date.today():
            raise ValueError("check_in_date cannot be in the past")
        return self


class BookingSummary(BaseModel):
    """Shown to the guest for explicit confirmation before anything is booked.

    This is the "I found a room for X nights at $Y total — would you like
    me to confirm this booking?" step. Nothing is written to the database
    until the guest confirms and the create-booking tool is called again
    with that confirmation (see agents/reservation/tools).
    """

    room: RoomOut
    check_in_date: date
    check_out_date: date
    nights: int
    guests: int
    total_price: Decimal


class ModifyBookingRequest(BaseModel):
    """Partial update — only the fields the guest wants to change are set."""

    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    guests: Optional[int] = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_date_range(self) -> "ModifyBookingRequest":
        if (
            self.check_in_date
            and self.check_out_date
            and self.check_out_date <= self.check_in_date
        ):
            raise ValueError("check_out_date must be after check_in_date")
        return self


class BookingOut(BaseModel):
    """A booking as returned to clients. Never expose other guests' bookings
    through this schema — the API layer must filter by the authenticated
    user's id (or require staff role) before a booking reaches here."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    check_in_date: date
    check_out_date: date
    guests: int
    status: str
    total_price: Decimal
    special_requests: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime] = None