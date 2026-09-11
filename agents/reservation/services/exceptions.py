class ReservationError(Exception):
    """Base class for all reservation domain errors.

    The API layer catches these and maps them to HTTP status codes. Keeping
    them separate from generic exceptions means a caller can distinguish
    "this booking doesn't exist" from "the database is unreachable."
    """


class RoomNotFoundError(ReservationError):
    """Raised when a room_id doesn't exist or is inactive."""


class RoomUnavailableError(ReservationError):
    """Raised when a room exists but can't be booked for the requested
    dates/guest count (double-booked, over capacity, wrong status, etc.)."""


class BookingNotFoundError(ReservationError):
    """Raised when a booking_id doesn't exist."""


class NotAuthorizedError(ReservationError):
    """Raised when the current user doesn't own the booking and isn't staff."""