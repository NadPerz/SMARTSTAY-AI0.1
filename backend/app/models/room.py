from sqlalchemy import Boolean, Column, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Room(Base):
    """A bookable hotel room.

    Reservation Agent owns this model. Rooms are the inventory that
    availability checks and bookings are validated against — this table,
    not the LLM, is the source of truth for what exists and what it costs.
    """

    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String, unique=True, nullable=False, index=True)
    room_type = Column(String, nullable=False)  # e.g. "Standard", "Deluxe", "Suite"
    description = Column(Text, nullable=True)
    capacity = Column(Integer, nullable=False)
    price_per_night = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    bookings = relationship("Booking", back_populates="room")

    def __repr__(self) -> str:
        return f"<Room {self.room_number} ({self.room_type})>"