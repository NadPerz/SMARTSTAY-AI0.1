"""Seed demo hotels and rooms for local development and manual API testing.

Safe to re-run: skips any hotel (matched by name+city) or room (matched by
hotel + room_number) that already exists, rather than creating duplicates.
Only touches the `hotels` and `rooms` tables — no bookings, no users.
Run database/init_db.py first if the tables don't exist yet.

Usage (from repo root, with backend/ on PYTHONPATH):
    PYTHONPATH=backend python database/seeds/demo_fixtures/seed_rooms.py
"""

from app.db.database import SessionLocal
from app.models.hotel import Hotel
from app.models.room import Room

# Booking.user relationship references "User" by name — must be imported
# somewhere in this process before any query touches Room/Booking mappers,
# since this script runs standalone.
from app.models.booking import Booking  # noqa: F401
from app.models.user import User  # noqa: F401

# Five hotels spread across different areas of Sri Lanka, each with a
# small, realistic room mix — enough to demonstrate cross-hotel,
# cross-city search without needing a huge dataset.
DEMO_HOTELS = [
    {
        "name": "Ocean Breeze Colombo",
        "city": "Colombo",
        "address": "42 Galle Road, Colombo 03",
        "description": "A modern city hotel close to Galle Face Green, popular with business travelers.",
        "star_rating": 4,
        "rooms": [
            {"room_number": "101", "room_type": "Standard", "capacity": 2, "price_per_night": 65.00,
             "description": "Compact city-view room with a queen bed."},
            {"room_number": "201", "room_type": "Deluxe", "capacity": 2, "price_per_night": 110.00,
             "description": "Spacious room with a king bed and ocean glimpse."},
            {"room_number": "301", "room_type": "Suite", "capacity": 4, "price_per_night": 220.00,
             "description": "Two-room suite with a living area, ideal for families."},
        ],
    },
    {
        "name": "Hill Crest Kandy",
        "city": "Kandy",
        "address": "18 Lake Drive, Kandy",
        "description": "A quiet hillside hotel overlooking Kandy Lake, near the Temple of the Tooth.",
        "star_rating": 3,
        "rooms": [
            {"room_number": "101", "room_type": "Standard", "capacity": 2, "price_per_night": 45.00,
             "description": "Cozy room with a lake-facing balcony."},
            {"room_number": "102", "room_type": "Standard", "capacity": 3, "price_per_night": 55.00,
             "description": "Triple room with garden view, good for small families."},
            {"room_number": "201", "room_type": "Deluxe", "capacity": 2, "price_per_night": 80.00,
             "description": "Deluxe room with a private terrace overlooking the lake."},
        ],
    },
    {
        "name": "Fort Heritage Galle",
        "city": "Galle",
        "address": "9 Church Street, Galle Fort",
        "description": "A restored colonial-era building inside the historic Galle Fort.",
        "star_rating": 5,
        "rooms": [
            {"room_number": "1", "room_type": "Deluxe", "capacity": 2, "price_per_night": 140.00,
             "description": "Heritage room with original teak flooring and antique furniture."},
            {"room_number": "2", "room_type": "Suite", "capacity": 3, "price_per_night": 260.00,
             "description": "Courtyard-facing suite with a private sitting area."},
        ],
    },
    {
        "name": "Ella Valley Retreat",
        "city": "Ella",
        "address": "Passara Road, Ella",
        "description": "A small guesthouse with panoramic views of the Ella Gap.",
        "star_rating": 3,
        "rooms": [
            {"room_number": "A1", "room_type": "Standard", "capacity": 2, "price_per_night": 35.00,
             "description": "Simple room with a private balcony facing the valley."},
            {"room_number": "A2", "room_type": "Standard", "capacity": 2, "price_per_night": 35.00,
             "description": "Twin-bed room, popular with backpackers."},
            {"room_number": "B1", "room_type": "Deluxe", "capacity": 4, "price_per_night": 70.00,
             "description": "Family room with two bedrooms and a shared balcony."},
        ],
    },
    {
        "name": "Negombo Beach Resort",
        "city": "Negombo",
        "address": "Lewis Place, Negombo",
        "description": "A beachfront resort close to the airport, popular for first/last-night stays.",
        "star_rating": 4,
        "rooms": [
            {"room_number": "101", "room_type": "Standard", "capacity": 2, "price_per_night": 55.00,
             "description": "Garden-view room a short walk from the beach."},
            {"room_number": "201", "room_type": "Deluxe", "capacity": 2, "price_per_night": 95.00,
             "description": "Beachfront room with a private balcony and sea view."},
            {"room_number": "301", "room_type": "Suite", "capacity": 4, "price_per_night": 180.00,
             "description": "Two-bedroom beachfront suite with a private terrace."},
        ],
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        hotels_created = 0
        rooms_created = 0
        rooms_skipped = 0

        for hotel_data in DEMO_HOTELS:
            rooms = hotel_data.pop("rooms")
            hotel = (
                db.query(Hotel)
                .filter(Hotel.name == hotel_data["name"], Hotel.city == hotel_data["city"])
                .first()
            )
            if hotel is None:
                hotel = Hotel(**hotel_data)
                db.add(hotel)
                db.flush()  # assign hotel.id without a full commit yet
                hotels_created += 1

            for room_data in rooms:
                existing_room = (
                    db.query(Room)
                    .filter(
                        Room.hotel_id == hotel.id,
                        Room.room_number == room_data["room_number"],
                    )
                    .first()
                )
                if existing_room:
                    rooms_skipped += 1
                    continue
                db.add(Room(hotel_id=hotel.id, **room_data))
                rooms_created += 1

        db.commit()
        print(
            f"Seeded {hotels_created} new hotel(s) and {rooms_created} new room(s) "
            f"(skipped {rooms_skipped} room(s) already present)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
