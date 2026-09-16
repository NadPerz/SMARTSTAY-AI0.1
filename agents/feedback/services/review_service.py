from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.review import Review, ReviewAspect

from agents.feedback.schemas.reviews import ReviewCreateRequest
from agents.feedback.services import nlp_engine
from agents.feedback.services.exceptions import ReviewNotFoundError


def create_review(db: Session, user_id: int, request: ReviewCreateRequest) -> Review:
    """Persist a guest review, running it through the NLP engine first so
    overall_sentiment/sentiment_score and the per-aspect ReviewAspect rows
    are derived server-side — a client can never submit its own sentiment
    (see ReviewCreateRequest, which has no such field)."""
    overall_label, overall_score = nlp_engine.overall_sentiment(request.review_text)
    aspect_hits = nlp_engine.extract_aspect_sentiments(request.review_text)

    review = Review(
        user_id=user_id,
        hotel_id=request.hotel_id,
        rating=request.rating,
        review_text=request.review_text,
        overall_sentiment=overall_label,
        sentiment_score=overall_score,
    )
    db.add(review)
    db.flush()  # assigns review.id, needed to attach ReviewAspect rows below

    for hit in aspect_hits:
        db.add(
            ReviewAspect(
                review_id=review.id,
                aspect=hit["aspect"],
                sentiment=hit["sentiment"],
                confidence=hit["confidence"],
                snippet=hit["snippet"],
            )
        )

    db.commit()
    db.refresh(review)
    return review


def get_review(db: Session, review_id: int) -> Review:
    review = db.query(Review).filter(Review.id == review_id).first()
    if review is None:
        raise ReviewNotFoundError(f"Review {review_id} not found")
    return review


def list_reviews(db: Session, hotel_id: Optional[int] = None) -> List[Review]:
    query = db.query(Review)
    if hotel_id is not None:
        query = query.filter(Review.hotel_id == hotel_id)
    return query.order_by(Review.created_at.desc()).all()
