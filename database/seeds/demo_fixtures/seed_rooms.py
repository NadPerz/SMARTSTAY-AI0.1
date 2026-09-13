"""Seed demo rooms for local development and manual API testing.

Safe to re-run: skips any room_number that already exists rather than
creating duplicates. Only touches the `rooms` table — no bookings, no
users. Run database/init_db.py first if the tables don't exist yet.

Usage (from repo root, with backend/ on PYTHONPATH):
    PYTHONPATH=backend python database/seeds/demo_fixtures/seed_rooms.py
"""

from app.db.database import SessionLocal
from app.models.room import Room

# Room.bookings and Booking.user are relationship() calls that reference
# "Booking"/"User" by name. SQLAlchemy can't resolve those strings unless
# both classes have been imported somewhere in this process first — this
# script runs standalone, so it must import them here even though they're
# otherwise unused directly.
from app.models.booking import Booking  # noqa: F401
from app.models.user import User  # noqa: F401

DEMO_ROOMS = [
    {
        "room_number": "101",
        "room_type": "Standard",
        "description": "Cozy standard room with a queen bed and city view.",
        "capacity": 2,
        "price_per_night": 80.00,
    },
    {
        "room_number": "102",
        "room_type": "Standard",
        "description": "Standard room with two twin beds, ideal for friends or colleagues.",
        "capacity": 2,
        "price_per_night": 80.00,
    },
    {
        "room_number": "201",
        "room_type": "Deluxe",
        "description": "Spacious deluxe room with a king bed and private balcony.",
        "capacity": 2,
        "price_per_night": 140.00,
    },
    {
        "room_number": "202",
        "room_type": "Deluxe",
        "description": "Deluxe room with a king bed, sofa, and garden view.",
        "capacity": 3,
        "price_per_night": 160.00,
    },
    {
        "room_number": "301",
        "room_type": "Suite",
        "description": "Two-bedroom suite with a living area, perfect for families.",
        "capacity": 4,
        "price_per_night": 260.00,
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        created = 0
        for data in DEMO_ROOMS:
            already_exists = (
                db.query(Room)
                .filter(Room.room_number == data["room_number"])
                .first()
            )
            if already_exists:
                continue
            db.add(Room(**data))
            created += 1
        db.commit()
        skipped = len(DEMO_ROOMS) - created
        print(f"Seeded {created} new room(s), skipped {skipped} already present.")
    finally:
        db.close()


if __name__ == "__main__":
    main()