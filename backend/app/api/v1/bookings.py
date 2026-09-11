from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.security.jwt import get_current_user

from agents.reservation.schemas.bookings import (
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
    BookingOut,
    BookingSummary,
    CreateBookingRequest,
    ModifyBookingRequest,
)
from agents.reservation.schemas.rooms import RoomSearchRequest, RoomSearchResult
from agents.reservation.services import availability_service, booking_service
from agents.reservation.services.exceptions import (
    BookingNotFoundError,
    NotAuthorizedError,
    RoomNotFoundError,
    RoomUnavailableError,
)

router = APIRouter(tags=["reservations"])


# --- Rooms ------------------------------------------------------------

@router.get("/rooms/search", response_model=List[RoomSearchResult])
def search_rooms(
    check_in_date: date = Query(...),
    check_out_date: date = Query(...),
    guests: int = Query(..., ge=1, le=20),
    room_type: Optional[str] = Query(default=None),
    max_price: Optional[Decimal] = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    """Public search — no authentication required, matching the guest
    website's room browsing flow (you don't need an account to look)."""
    try:
        request = RoomSearchRequest(
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
            room_type=room_type,
            max_price=max_price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return availability_service.search_available_rooms(db, request)


@router.get("/rooms/{room_id}/availability", response_model=AvailabilityCheckResponse)
def check_room_availability(
    room_id: int,
    check_in_date: date = Query(...),
    check_out_date: date = Query(...),
    guests: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    try:
        request = AvailabilityCheckRequest(
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        return availability_service.check_room_availability(
            db, request.room_id, request.check_in_date, request.check_out_date, request.guests
        )
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Bookings -----------------------------------------------------------

@router.post("/bookings/summary", response_model=BookingSummary)
def get_booking_summary(
    request: CreateBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """What the frontend calls to render the "confirm this booking?" screen
    before the guest clicks the real confirm button. Requires auth (same as
    create_booking) even though it doesn't write anything, so a guest is
    always logged in by the time they see pricing tied to an account."""
    try:
        return booking_service.build_booking_summary(db, request)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RoomUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    request: CreateBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a booking for the AUTHENTICATED guest. There's no separate
    "confirm" flag here (unlike the agent tool) because the UI flow itself
    is the confirmation: the frontend calls /bookings/summary first, shows
    it to the guest, and only calls this endpoint after they click confirm.
    The backend still re-validates everything (capacity, double-booking)
    regardless of what the UI already showed."""
    try:
        return booking_service.create_booking(db, current_user.id, request)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RoomUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/bookings", response_model=List[BookingOut])
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return booking_service.list_bookings_for_user(db, current_user.id)


@router.get("/bookings/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return booking_service.get_booking(db, booking_id, current_user)
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotAuthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.patch("/bookings/{booking_id}", response_model=BookingOut)
def modify_booking(
    booking_id: int,
    request: ModifyBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return booking_service.modify_booking(db, booking_id, current_user, request)
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotAuthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except RoomUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.delete("/bookings/{booking_id}", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DELETE here means "cancel", matching the project's API design —
    the row isn't removed, its status becomes CANCELLED so booking history
    is preserved."""
    try:
        return booking_service.cancel_booking(db, booking_id, current_user)
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotAuthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except RoomUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))