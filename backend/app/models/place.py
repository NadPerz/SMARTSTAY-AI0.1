from sqlalchemy import Boolean, Column, Index, Integer, Numeric, String, Text

from app.db.database import Base


class Place(Base):
    """A recommendable place: restaurant, attraction, activity, shopping,
    or entertainment venue. Independent of any single Hotel — a place is
    "nearby" in the sense that it shares a city with the guest's hotel,
    not because it's owned by that hotel (unlike Room, which belongs to
    exactly one Hotel).

    Recommendation Agent owns this model. `description` is the field that
    gets embedded for semantic search (see
    agents/recommendation/services/retrieval_service.py) — write it as a
    few natural sentences, not a keyword list, since that's what the
    embedding model was trained to compare against free-text guest queries.

    `tags` is a plain comma-separated string rather than a Postgres ARRAY
    column so this table behaves identically on the SQLite in-memory
    databases the test suite uses and on Postgres in production — the same
    portability trade-off the rest of this codebase makes (see
    BookingStatus using a plain String column instead of a native enum
    type).
    """

    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)

    # "restaurant" | "attraction" | "activity" | "shopping" | "entertainment"
    # Kept as a plain String (validated at the Pydantic layer via
    # PlaceCategory) rather than a DB-level enum, matching how
    # BookingStatus is handled elsewhere in this codebase.
    category = Column(String, nullable=False, index=True)

    # Only meaningful for category == "restaurant"; NULL otherwise.
    cuisine = Column(String, nullable=True, index=True)

    city = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True)

    # The text that gets chunked/embedded for semantic search. Also shown
    # to the guest, so it should read naturally on its own.
    description = Column(Text, nullable=False)

    # "budget" | "moderate" | "premium" — see PlaceBudgetTier.
    budget_tier = Column(String, nullable=False, index=True)

    # 1.0-5.0, optional (not every seeded place needs a rating).
    rating = Column(Numeric(2, 1), nullable=True)

    # Comma-separated free-form tags, e.g. "romantic,outdoor,live-music".
    # Used as extra keyword-search surface, not structurally validated.
    tags = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_places_city_category_active", "city", "category", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Place {self.name} ({self.category}, {self.city})>"