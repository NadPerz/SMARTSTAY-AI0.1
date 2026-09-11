from typing import Any, Dict, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.user import User

from agents.reservation.schemas.bookings import (
    BookingSummary,
    CreateBookingRequest,
    ModifyBookingRequest,
)
from agents.reservation.schemas.rooms import RoomOut
from agents.reservation.services import availability_service, booking_service
from agents.reservation.services.exceptions import (
    BookingNotFoundError,
    NotAuthorizedError,
    RoomNotFoundError,
    RoomUnavailableError,
)
from agents.reservation.tools.utils import format_validation_error, serialize_booking


def get_booking_summary(
    db: Session,
    room_id: int,
    check_in_date: str,
    check_out_date: str,
    guests: int,
    special_requests: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool: build the "would you like me to confirm this booking?" summary.

    Read-only — does NOT write anything to the database. This is what the
    agent must show the guest and get explicit agreement on BEFORE calling
    create_booking(confirm=True). This is the "show booking summary, ask
    confirmation" step in the booking safety flow, not a formality.
    """
    try:
        request = CreateBookingRequest(
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
            special_requests=special_requests,
        )
    except ValidationError as exc:
        return {"success": False, "error": format_validation_error(exc)}

    try:
        room = availability_service.get_room(db, request.room_id)
        availability = availability_service.check_room_availability(
            db,
            request.room_id,
            request.check_in_date,
            request.check_out_date,
            request.guests,
        )
    except RoomNotFoundError as exc:
        return {"success": False, "error": str(exc)}

    if not availability.is_available:
        return {"success": False, "error": availability.reason or "Room is not available"}

    summary = BookingSummary(
        room=RoomOut.model_validate(room),
        check_in_date=request.check_in_date,
        check_out_date=request.check_out_date,
        nights=availability.nights,
        guests=request.guests,
        total_price=availability.total_price,
    )
    return {"success": True, "data": summary.model_dump(mode="json")}


def create_booking(
    db: Session,
    current_user: User,
    room_id: int,
    check_in_date: str,
    check_out_date: str,
    guests: int,
    confirm: bool = False,
    special_requests: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool: create a booking. WRITE OPERATION — refuses unless confirm=True.

    This is the actual enforcement point for "never tell the guest a
    booking is confirmed unless the backend confirms it": if confirm is
    not explicitly True, nothing is written and the caller is told to show
    get_booking_summary() to the guest first. `current_user` must come
    from get_current_user at the API layer — never from client input.
    """
    if not confirm:
        return {
            "success": False,
            "error": (
                "Booking requires explicit confirmation. Call get_booking_summary "
                "first, show it to the guest, and only call create_booking again "
                "with confirm=True after the guest explicitly agrees."
            ),
        }

    try:
        request = CreateBookingRequest(
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
            special_requests=special_requests,
        )
    except ValidationError as exc:
        return {"success": False, "error": format_validation_error(exc)}

    try:
        booking = booking_service.create_booking(db, current_user.id, request)
    except (RoomNotFoundError, RoomUnavailableError) as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "data": serialize_booking(booking)}


def get_booking(db: Session, current_user: User, booking_id: int) -> Dict[str, Any]:
    """Tool: fetch one booking. Enforces owner-or-staff access."""
    try:
        booking = booking_service.get_booking(db, booking_id, current_user)
    except (BookingNotFoundError, NotAuthorizedError) as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "data": serialize_booking(booking)}


def list_my_bookings(db: Session, current_user: User) -> Dict[str, Any]:
    """Tool: list all bookings belonging to the authenticated guest."""
    bookings = booking_service.list_bookings_for_user(db, current_user.id)
    return {
        "success": True,
        "data": {
            "count": len(bookings),
            "bookings": [serialize_booking(b) for b in bookings],
        },
    }


def modify_booking(
    db: Session,
    current_user: User,
    booking_id: int,
    check_in_date: Optional[str] = None,
    check_out_date: Optional[str] = None,
    guests: Optional[int] = None,
) -> Dict[str, Any]:
    """Tool: modify an existing booking's dates/guest count.

    Only the fields provided are changed. Re-runs the double-booking check
    against the new dates before writing.
    """
    try:
        request = ModifyBookingRequest(
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
        )
    except ValidationError as exc:
        return {"success": False, "error": format_validation_error(exc)}

    try:
        booking = booking_service.modify_booking(db, booking_id, current_user, request)
    except (BookingNotFoundError, NotAuthorizedError, RoomUnavailableError) as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "data": serialize_booking(booking)}


def cancel_booking(
    db: Session, current_user: User, booking_id: int, confirm: bool = False
) -> Dict[str, Any]:
    """Tool: cancel a booking. WRITE OPERATION — refuses unless confirm=True.

    Same confirmation gate as create_booking, for the same reason:
    cancellation is a consequential action and must not happen just
    because the LLM inferred that's what the guest probably wants.
    """
    if not confirm:
        return {
            "success": False,
            "error": (
                "Cancellation requires explicit confirmation. Confirm with the "
                "guest, then call cancel_booking again with confirm=True."
            ),
        }

    try:
        booking = booking_service.cancel_booking(db, booking_id, current_user)
    except (BookingNotFoundError, NotAuthorizedError, RoomUnavailableError) as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "data": serialize_booking(booking)}