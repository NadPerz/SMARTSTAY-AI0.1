from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.models.user import User

from agents.reservation.schemas.bookings import (
    BookingSummary,
    CreateBookingRequest,
    ModifyBookingRequest,
)
from agents.reservation.schemas.rooms import RoomOut
from agents.reservation.services.availability_service import (
    _nights,
    check_room_availability,
    get_room,
    has_overlapping_booking,
)
from agents.reservation.services.exceptions import (
    BookingNotFoundError,
    NotAuthorizedError,
    RoomNotFoundError,
    RoomUnavailableError,
)

# MVP simplification: this repo doesn't have a defined RBAC role set yet
# (only User.role, defaulting to "guest"). Anyone with a non-guest role is
# treated as staff for booking access purposes. Revisit once the team
# settles on a real role enum (Receptionist/Manager/Admin/Analyst).
def _is_staff(user: User) -> bool:
    return user.role != "guest"


def build_booking_summary(db: Session, request: CreateBookingRequest) -> BookingSummary:
    """Build the "would you like to confirm this booking?" summary without
    writing anything to the database.

    Shared by the REST API's POST /api/bookings/summary endpoint and the
    Reservation Agent's get_booking_summary tool — there is exactly one
    place this logic lives, so the guest sees the same numbers whether
    they're using the web UI or talking to the AI concierge.
    """
    room = get_room(db, request.room_id)
    availability = check_room_availability(
        db,
        request.room_id,
        request.check_in_date,
        request.check_out_date,
        request.guests,
    )
    if not availability.is_available:
        raise RoomUnavailableError(availability.reason or "Room is not available")

    return BookingSummary(
        room=RoomOut.model_validate(room),
        check_in_date=request.check_in_date,
        check_out_date=request.check_out_date,
        nights=availability.nights,
        guests=request.guests,
        total_price=availability.total_price,
    )


def create_booking(db: Session, user_id: int, request: CreateBookingRequest) -> Booking:
    """Create a booking for the AUTHENTICATED user only.

    `user_id` must be supplied by the caller from `get_current_user` at the
    API layer — never from `request`, which has no user_id field by design.
    By the time this is called, the guest has already seen a BookingSummary
    and explicitly confirmed (that confirmation step happens one layer up,
    in the tool/agent — this function assumes confirmation already happened
    and just does the validated write).
    """
    room = (
        db.query(Room)
        .filter(Room.id == request.room_id, Room.is_active.is_(True))
        .first()
    )
    if room is None:
        raise RoomNotFoundError(f"Room {request.room_id} does not exist or is inactive")

    if request.guests > room.capacity:
        raise RoomUnavailableError(
            f"Room capacity is {room.capacity}, requested {request.guests} guests"
        )

    # Re-check the overlap right before writing. The guest may have seen
    # search results or an availability check some time ago — another
    # booking could have been made in the meantime. This is the
    # application-layer half of double-booking protection; a DB-level
    # constraint is the second, independent layer (see docs).
    if has_overlapping_booking(
        db, room.id, request.check_in_date, request.check_out_date
    ):
        raise RoomUnavailableError("Room is no longer available for these dates")

    nights = _nights(request.check_in_date, request.check_out_date)
    total_price = room.price_per_night * nights

    booking = Booking(
        user_id=user_id,
        room_id=room.id,
        check_in_date=request.check_in_date,
        check_out_date=request.check_out_date,
        guests=request.guests,
        status=BookingStatus.CONFIRMED.value,
        total_price=total_price,
        special_requests=request.special_requests,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_booking(db: Session, booking_id: int, current_user: User) -> Booking:
    """Fetch a booking, enforcing that only its owner or staff can see it."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise BookingNotFoundError(f"Booking {booking_id} does not exist")
    if booking.user_id != current_user.id and not _is_staff(current_user):
        raise NotAuthorizedError("You do not have permission to view this booking")
    return booking


def list_bookings_for_user(db: Session, user_id: int) -> List[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.check_in_date)
        .all()
    )


def modify_booking(
    db: Session, booking_id: int, current_user: User, request: ModifyBookingRequest
) -> Booking:
    booking = get_booking(db, booking_id, current_user)  # reuses ownership check

    if booking.status not in BookingStatus.active_statuses():
        raise RoomUnavailableError("Only pending or confirmed bookings can be modified")

    new_check_in = request.check_in_date or booking.check_in_date
    new_check_out = request.check_out_date or booking.check_out_date
    new_guests = request.guests or booking.guests

    room = db.query(Room).filter(Room.id == booking.room_id).first()
    if new_guests > room.capacity:
        raise RoomUnavailableError(
            f"Room capacity is {room.capacity}, requested {new_guests} guests"
        )

    if has_overlapping_booking(
        db, booking.room_id, new_check_in, new_check_out, exclude_booking_id=booking.id
    ):
        raise RoomUnavailableError("Room is not available for the new dates")

    booking.check_in_date = new_check_in
    booking.check_out_date = new_check_out
    booking.guests = new_guests
    booking.total_price = room.price_per_night * _nights(new_check_in, new_check_out)
    db.commit()
    db.refresh(booking)
    return booking


def cancel_booking(db: Session, booking_id: int, current_user: User) -> Booking:
    booking = get_booking(db, booking_id, current_user)
    if booking.status == BookingStatus.CANCELLED.value:
        raise RoomUnavailableError("Booking is already cancelled")

    booking.status = BookingStatus.CANCELLED.value
    booking.cancelled_at = datetime.utcnow()
    db.commit()
    db.refresh(booking)
    return booking