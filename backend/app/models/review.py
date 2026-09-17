from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class Review(Base):
    """A guest's free-text review of a stay, plus the sentiment the
    Feedback Agent's NLP engine derived from it.

    Feedback Agent owns this model. `user_id` is always taken from the
    authenticated session (never client input), matching the same rule
    Reservation Agent's Booking model follows.

    `hotel_id` is a plain, unconstrained column (no ForeignKey) on purpose:
    the Hotel table only exists on the not-yet-merged
    feature/reservation-agent branch. Once both branches merge into main,
    this should become a real ForeignKey("hotels.id").
    """

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hotel_id = Column(Integer, nullable=True, index=True)

    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=False)

    # Populated by agents.feedback.services.nlp_engine at creation time.
    overall_sentiment = Column(String, nullable=True)
    sentiment_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    aspects = relationship(
        "ReviewAspect", back_populates="review", cascade="all, delete-orphan"
    )
    user = relationship("User")

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )

    def __repr__(self) -> str:
        return f"<Review id={self.id} user_id={self.user_id} rating={self.rating}>"


class ReviewAspect(Base):
    """One aspect (e.g. "breakfast", "staff") extracted from a Review's
    text, with the sentiment expressed about it in that specific clause.

    A single review can mention several aspects with different sentiment
    ("room was beautiful but breakfast was slow") — that's exactly what
    this table is for: it's a one-to-many child of Review, not a column
    on it.
    """

    __tablename__ = "review_aspects"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)

    aspect = Column(String, nullable=False, index=True)
    sentiment = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    snippet = Column(Text, nullable=False)

    review = relationship("Review", back_populates="aspects")

    def __repr__(self) -> str:
        return f"<ReviewAspect review_id={self.review_id} aspect={self.aspect} sentiment={self.sentiment}>"
