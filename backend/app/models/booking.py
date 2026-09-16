import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class BookingStatus(str, enum.Enum):
    """Booking lifecycle states.

    PENDING and CONFIRMED are the only states that count as "active" for
    double-booking overlap checks. CANCELLED bookings free up the room.
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

    @classmethod
    def active_statuses(cls) -> tuple[str, ...]:
        """Statuses that still hold the room and must be checked for overlaps."""
        return (cls.PENDING.value, cls.CONFIRMED.value)


class Booking(Base):
    """A reservation of a room by a user for a date range.

    Reservation Agent owns this model. `user_id` must ALWAYS be set from the
    authenticated session on the backend — never accepted from client input —
    to prevent a guest from creating or viewing a booking under someone
    else's account.
    """

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)

    # Derived from the authenticated session server-side. Never trust a
    # client-supplied user_id for this field.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)

    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    guests = Column(Integer, nullable=False)

    status = Column(
        String,
        nullable=False,
        default=BookingStatus.PENDING.value,
    )

    total_price = Column(Numeric(10, 2), nullable=False)
    special_requests = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    cancelled_at = Column(DateTime, nullable=True)

    room = relationship("Room", back_populates="bookings")
    user = relationship("User")

    __table_args__ = (
        # Basic sanity check at the DB level — cheap and catches bad data
        # regardless of which layer of the app tried to write it.
        CheckConstraint(
            "check_out_date > check_in_date", name="ck_booking_dates_valid"
        ),
        # Speeds up the overlap query the double-booking check runs on
        # every create/modify request (filter by room_id + status, then
        # compare date ranges).
        Index("ix_bookings_room_status", "room_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} room_id={self.room_id} "
            f"user_id={self.user_id} status={self.status}>"
        )