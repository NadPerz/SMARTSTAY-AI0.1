from typing import Any, Dict, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from agents.reservation.schemas.bookings import AvailabilityCheckRequest
from agents.reservation.schemas.rooms import RoomSearchRequest
from agents.reservation.services import availability_service
from agents.reservation.services.exceptions import RoomNotFoundError
from agents.reservation.tools.utils import format_validation_error


def search_rooms(
    db: Session,
    check_in_date: str,
    check_out_date: str,
    guests: int,
    room_type: Optional[str] = None,
    max_price: Optional[float] = None,
) -> Dict[str, Any]:
    """Tool: find rooms available for a date range.

    Read-only. Deterministic — the LLM only decides WHEN to call this and
    with WHAT arguments; all matching/pricing logic lives in
    availability_service, not here and not in the LLM.
    """
    try:
        request = RoomSearchRequest(
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
            room_type=room_type,
            max_price=max_price,
        )
    except ValidationError as exc:
        return {"success": False, "error": format_validation_error(exc)}

    results = availability_service.search_available_rooms(db, request)
    return {
        "success": True,
        "data": {
            "count": len(results),
            "rooms": [r.model_dump(mode="json") for r in results],
        },
    }


def check_availability(
    db: Session,
    room_id: int,
    check_in_date: str,
    check_out_date: str,
    guests: int,
) -> Dict[str, Any]:
    """Tool: check whether ONE specific room is available for a date range."""
    try:
        request = AvailabilityCheckRequest(
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
        )
    except ValidationError as exc:
        return {"success": False, "error": format_validation_error(exc)}

    try:
        result = availability_service.check_room_availability(
            db,
            request.room_id,
            request.check_in_date,
            request.check_out_date,
            request.guests,
        )
    except RoomNotFoundError as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "data": result.model_dump(mode="json")}