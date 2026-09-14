from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Hotel(Base):
    """A single hotel property in a specific city.

    SmartStay AI, as a multi-hotel aggregator, lets a guest search across
    every hotel on the platform or narrow down to one city/hotel first.
    Every Room belongs to exactly one Hotel — a "nearby restaurant"
    recommendation is only meaningful relative to a specific hotel's
    location, so this relationship is required, not optional.
    """

    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    star_rating = Column(Integer, nullable=True)  # 1-5, optional

    rooms = relationship("Room", back_populates="hotel")

    def __repr__(self) -> str:
        return f"<Hotel {self.name} ({self.city})>"
