from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class Room(Base):
    """A bookable hotel room, belonging to exactly one Hotel.

    Reservation Agent owns this model. Rooms are the inventory that
    availability checks and bookings are validated against — this table,
    not the LLM, is the source of truth for what exists and what it costs.
    """

    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False, index=True)
    room_number = Column(String, nullable=False, index=True)
    room_type = Column(String, nullable=False)  # e.g. "Standard", "Deluxe", "Suite"
    description = Column(Text, nullable=True)
    capacity = Column(Integer, nullable=False)
    price_per_night = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    hotel = relationship("Hotel", back_populates="rooms")
    bookings = relationship("Booking", back_populates="room")

    __table_args__ = (
        # room_number only needs to be unique WITHIN a hotel — two
        # different hotels can each have a "Room 101".
        UniqueConstraint("hotel_id", "room_number", name="uq_room_hotel_number"),
    )

    def __repr__(self) -> str:
        return f"<Room {self.room_number} ({self.room_type}) at hotel {self.hotel_id}>"