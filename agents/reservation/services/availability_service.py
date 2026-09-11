from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.room import Room

from agents.reservation.schemas.bookings import AvailabilityCheckResponse
from agents.reservation.schemas.rooms import RoomOut, RoomSearchRequest, RoomSearchResult
from agents.reservation.services.exceptions import RoomNotFoundError


def _nights(check_in_date: date, check_out_date: date) -> int:
    return (check_out_date - check_in_date).days


def has_overlapping_booking(
    db: Session,
    room_id: int,
    check_in_date: date,
    check_out_date: date,
    exclude_booking_id: Optional[int] = None,
) -> bool:
    """The core double-booking guard.

    Two half-open date ranges [a_start, a_end) and [b_start, b_end) overlap
    if and only if a_start < b_end AND a_end > b_start. Only PENDING/
    CONFIRMED bookings hold the room — a CANCELLED booking frees it up.

    `exclude_booking_id` lets modify_booking() check a booking's *new*
    dates without the booking's own current row counting as a conflict
    with itself.
    """
    query = db.query(Booking).filter(
        Booking.room_id == room_id,
        Booking.status.in_(BookingStatus.active_statuses()),
        Booking.check_in_date < check_out_date,
        Booking.check_out_date > check_in_date,
    )
    if exclude_booking_id is not None:
        query = query.filter(Booking.id != exclude_booking_id)
    return db.query(query.exists()).scalar()


def search_available_rooms(
    db: Session, request: RoomSearchRequest
) -> List[RoomSearchResult]:
    """Return active rooms matching the filters that have no overlapping
    booking for the requested date range, with pricing computed."""
    query = db.query(Room).filter(
        Room.is_active.is_(True),
        Room.capacity >= request.guests,
    )
    if request.room_type:
        query = query.filter(Room.room_type == request.room_type)
    if request.max_price is not None:
        query = query.filter(Room.price_per_night <= request.max_price)

    nights = _nights(request.check_in_date, request.check_out_date)
    results: List[RoomSearchResult] = []
    for room in query.all():
        if has_overlapping_booking(
            db, room.id, request.check_in_date, request.check_out_date
        ):
            continue
        results.append(
            RoomSearchResult(
                room=RoomOut.model_validate(room),
                nights=nights,
                total_price=room.price_per_night * nights,
            )
        )
    return results


def check_room_availability(
    db: Session,
    room_id: int,
    check_in_date: date,
    check_out_date: date,
    guests: int,
) -> AvailabilityCheckResponse:
    """Availability check for one specific room, with a human-readable
    reason attached when it isn't available — used by the
    `check_availability` tool before the guest ever sees a booking summary."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise RoomNotFoundError(f"Room {room_id} does not exist")

    nights = _nights(check_in_date, check_out_date)

    if not room.is_active:
        return AvailabilityCheckResponse(
            room_id=room_id,
            is_available=False,
            reason="Room is not currently active",
            nights=nights,
        )
    if guests > room.capacity:
        return AvailabilityCheckResponse(
            room_id=room_id,
            is_available=False,
            reason=f"Room capacity is {room.capacity}, requested {guests} guests",
            nights=nights,
        )
    if has_overlapping_booking(db, room_id, check_in_date, check_out_date):
        return AvailabilityCheckResponse(
            room_id=room_id,
            is_available=False,
            reason="Room is already booked for part of this date range",
            nights=nights,
        )

    return AvailabilityCheckResponse(
        room_id=room_id,
        is_available=True,
        nights=nights,
        total_price=room.price_per_night * nights,
    )