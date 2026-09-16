from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.security.jwt import get_current_user

from agents.feedback.schemas.reviews import ReviewCreateRequest, ReviewOut
from agents.feedback.services import review_service
from agents.feedback.services.exceptions import ReviewNotFoundError

router = APIRouter(tags=["feedback"])


@router.post("/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def submit_review(
    request: ReviewCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a review for the AUTHENTICATED guest. Sentiment and
    per-aspect breakdown are computed server-side (see nlp_engine) and
    returned immediately — there's no separate "processing" step."""
    return review_service.create_review(db, current_user.id, request)


@router.get("/reviews", response_model=List[ReviewOut])
def list_reviews(
    hotel_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Public — browse reviews, optionally filtered to one hotel."""
    return review_service.list_reviews(db, hotel_id=hotel_id)


@router.get("/reviews/{review_id}", response_model=ReviewOut)
def get_review(review_id: int, db: Session = Depends(get_db)):
    try:
        return review_service.get_review(db, review_id)
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
