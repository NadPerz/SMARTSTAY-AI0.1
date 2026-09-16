from typing import Any, Dict, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.user import User

from agents.feedback.schemas.reviews import ReviewCreateRequest
from agents.feedback.services import review_service
from agents.feedback.services.exceptions import ReviewNotFoundError
from agents.feedback.tools.utils import format_validation_error, serialize_review


def submit_review(
    db: Session,
    current_user: User,
    rating: int,
    review_text: str,
    hotel_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Tool: submit a guest review. WRITE OPERATION, but — unlike booking
    creation/cancellation — has no confirm-gate: a review isn't a
    committed transaction with a financial/inventory consequence, so
    there's nothing to explicitly confirm before writing it.
    """
    try:
        request = ReviewCreateRequest(
            hotel_id=hotel_id, rating=rating, review_text=review_text
        )
    except ValidationError as exc:
        return {"success": False, "error": format_validation_error(exc)}

    review = review_service.create_review(db, current_user.id, request)
    return {"success": True, "data": serialize_review(review)}


def get_review(db: Session, review_id: int) -> Dict[str, Any]:
    """Tool: fetch one review, including its per-aspect sentiment."""
    try:
        review = review_service.get_review(db, review_id)
    except ReviewNotFoundError as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "data": serialize_review(review)}


def list_reviews(db: Session, hotel_id: Optional[int] = None) -> Dict[str, Any]:
    """Tool: list reviews, optionally filtered to one hotel."""
    reviews = review_service.list_reviews(db, hotel_id=hotel_id)
    return {
        "success": True,
        "data": {
            "count": len(reviews),
            "reviews": [serialize_review(r) for r in reviews],
        },
    }
