from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.hotel import Hotel
from app.models.room import Room

from agents.reservation.schemas.bookings import AvailabilityCheckResponse
from agents.reservation.schemas.hotels import HotelCreateRequest
from agents.reservation.schemas.rooms import (
    RoomCreateRequest,
    RoomOut,
    RoomSearchRequest,
    RoomSearchResult,
)
from agents.reservation.services.exceptions import (
    HotelNotFoundError,
    RoomAlreadyExistsError,
    RoomNotFoundError,
)


def _nights(check_in_date: date, check_out_date: date) -> int:
    return (check_out_date - check_in_date).days


# --- Hotels --------------------------------------------------------------

def get_hotel(db: Session, hotel_id: int) -> Hotel:
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if hotel is None:
        raise HotelNotFoundError(f"Hotel {hotel_id} does not exist")
    return hotel


def list_hotels(db: Session, city: Optional[str] = None) -> List[Hotel]:
    """List hotels on the platform, optionally filtered to one city.

    This is what a guest browsing by location (rather than searching by
    date/guests first) would call — "show me hotels in Kandy" before
    "show me available rooms."
    """
    query = db.query(Hotel)
    if city:
        query = query.filter(Hotel.city.ilike(city))
    return query.order_by(Hotel.city, Hotel.name).all()


def create_hotel(db: Session, request: HotelCreateRequest) -> Hotel:
    """Admin-only: add a new hotel to the platform. Authorization is
    enforced at the API layer, not here."""
    hotel = Hotel(
        name=request.name,
        city=request.city,
        address=request.address,
        description=request.description,
        star_rating=request.star_rating,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


# --- Rooms -----------------------------------------------------------------

def get_room(db: Session, room_id: int) -> Room:
    """Fetch a single room by id, or raise RoomNotFoundError.

    Used by tools that need the full Room object (e.g. to build a booking
    summary), as opposed to check_room_availability() which only returns
    a yes/no verdict.
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise RoomNotFoundError(f"Room {room_id} does not exist")
    return room


def create_room(db: Session, request: RoomCreateRequest) -> Room:
    """Admin-only: add a new room to a hotel's inventory.

    Authorization (staff-only) is enforced at the API layer, not here —
    this function assumes the caller has already been checked. Validates
    the hotel actually exists, and guards against a duplicate room_number
    WITHIN that hotel (two different hotels may reuse the same number)
    with a pre-check rather than relying on the DB's unique constraint to
    raise (which would surface as a raw IntegrityError instead of a clean,
    catchable domain exception).
    """
    get_hotel(db, request.hotel_id)  # raises HotelNotFoundError if missing

    existing = (
        db.query(Room)
        .filter(Room.hotel_id == request.hotel_id, Room.room_number == request.room_number)
        .first()
    )
    if existing is not None:
        raise RoomAlreadyExistsError(
            f"Room number {request.room_number!r} already exists at hotel {request.hotel_id}"
        )

    room = Room(
        hotel_id=request.hotel_id,
        room_number=request.room_number,
        room_type=request.room_type,
        description=request.description,
        capacity=request.capacity,
        price_per_night=request.price_per_night,
        is_active=request.is_active,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


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
    booking for the requested date range, with pricing computed.

    Searches across every hotel on the platform by default. Pass `city`
    to narrow to one city, or `hotel_id` to search within one specific
    hotel — both are optional and independent."""
    query = db.query(Room).join(Hotel).filter(
        Room.is_active.is_(True),
        Room.capacity >= request.guests,
    )
    if request.city:
        query = query.filter(Hotel.city.ilike(request.city))
    if request.hotel_id is not None:
        query = query.filter(Room.hotel_id == request.hotel_id)
    if request.room_type:
        query = query.filter(Room.room_type.ilike(f"%{request.room_type}%"))
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
