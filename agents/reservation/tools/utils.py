from typing import Any, Dict

from pydantic import ValidationError

from agents.reservation.schemas.bookings import BookingOut


def format_validation_error(exc: ValidationError) -> str:
    """Turn a Pydantic ValidationError into one short, guest-readable
    message instead of leaking the raw error structure back through the
    agent (which would look like an internal stack trace to the guest)."""
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"])
    return f"{field}: {first['msg']}"


def serialize_booking(booking) -> Dict[str, Any]:
    """SQLAlchemy Booking -> plain JSON-safe dict, via the BookingOut schema."""
    return BookingOut.model_validate(booking).model_dump(mode="json")