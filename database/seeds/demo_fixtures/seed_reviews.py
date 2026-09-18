"""Seed a demo guest and demo reviews for local development, manual API
testing, and giving the analytics dashboard something to show.

Safe to re-run: skips any review already present for the demo user with
the exact same review_text, rather than creating duplicates. Reviews are
created through review_service.create_review() - the same function the
real API uses - so sentiment/aspect data is computed the normal way, not
hardcoded, and stays consistent with whatever the NLP engine currently does.

Run database/init_db.py first if the tables don't exist yet.

Usage (from repo root, with backend/ on PYTHONPATH):
    PYTHONPATH=backend python database/seeds/demo_fixtures/seed_reviews.py
"""

from passlib.context import CryptContext

from app.db.database import SessionLocal
from app.models.hotel import Hotel
from app.models.review import Review
from app.models.user import User

# Hotel.rooms references "Room" by string name — must be imported
# somewhere in this process before any query touches the Hotel mapper,
# since this script runs standalone (same reason seed_rooms.py imports
# Booking/User).
from app.models.room import Room  # noqa: F401
from app.models.booking import Booking  # noqa: F401

from agents.feedback.schemas.reviews import ReviewCreateRequest
from agents.feedback.services import review_service

DEMO_GUEST_EMAIL = "demo.guest@smartstay.ai"
DEMO_GUEST_PASSWORD = "demo1234"  # local/demo data only - never a real account

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Deliberately varied: mixed-sentiment sentences, aspect overlaps, and a
# spread of ratings, so the analytics dashboard (sentiment breakdown, top
# positive/negative aspects, summary_text) has something meaningful to show
# instead of one flat result. hotel_id cycles through whatever hotels
# seed_rooms.py already created (falls back to 1 if none exist yet).
DEMO_REVIEWS = [
    {"rating": 5, "text": "Amazing location and very comfortable bed. The staff were incredibly friendly too."},
    {"rating": 2, "text": "The room was beautiful but breakfast was expensive and the staff were slow."},
    {"rating": 1, "text": "Terrible staff, rude and unhelpful. The room was also cramped and dirty."},
    {"rating": 4, "text": "Great value for the price. Room was clean and the location was very convenient."},
    {"rating": 3, "text": "The location was amazing but the room was dirty and outdated."},
    {"rating": 5, "text": "Superb stay, the concierge was phenomenal and check-in was fast."},
    {"rating": 2, "text": "Hotel room is good but staff is not good and breakfast was overpriced."},
    {"rating": 4, "text": "Spacious room, attentive staff, and a quiet night's sleep."},
    {"rating": 1, "text": "Overpriced for what it is. Noisy at night and the staff were unfriendly."},
    {"rating": 3, "text": "Breakfast was expensive but the room was spacious and comfortable."},
    {"rating": 5, "text": "Excellent service from check-in to checkout. Loved the clean, welcoming room."},
    {"rating": 2, "text": "The pool was gross and the wifi was atrocious. Staff did try to help though."},
]


def _get_or_create_demo_user(db) -> User:
    user = db.query(User).filter(User.email == DEMO_GUEST_EMAIL).first()
    if user is not None:
        return user
    user = User(
        email=DEMO_GUEST_EMAIL,
        password_hash=pwd_context.hash(DEMO_GUEST_PASSWORD),
        role="guest",
    )
    db.add(user)
    db.flush()  # assign user.id without a full commit yet
    return user


def _demo_hotel_ids(db) -> list:
    """Reuse whatever hotels seed_rooms.py already created, so reviews
    line up with real demo hotels when both seed scripts have been run.
    Falls back to a single placeholder id if none exist yet - hotel_id has
    no ForeignKey constraint (see backend/app/models/review.py), so this
    is safe either way."""
    ids = [hotel_id for (hotel_id,) in db.query(Hotel.id).order_by(Hotel.id).all()]
    return ids or [1]


def main() -> None:
    db = SessionLocal()
    try:
        user = _get_or_create_demo_user(db)
        hotel_ids = _demo_hotel_ids(db)

        existing_texts = {
            text
            for (text,) in db.query(Review.review_text)
            .filter(Review.user_id == user.id)
            .all()
        }

        created = 0
        skipped = 0
        for i, item in enumerate(DEMO_REVIEWS):
            if item["text"] in existing_texts:
                skipped += 1
                continue
            request = ReviewCreateRequest(
                hotel_id=hotel_ids[i % len(hotel_ids)],
                rating=item["rating"],
                review_text=item["text"],
            )
            review_service.create_review(db, user.id, request)
            created += 1

        print(
            f"Seeded {created} new review(s) for {DEMO_GUEST_EMAIL} "
            f"(skipped {skipped} already present)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
