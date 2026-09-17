from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.security.jwt import get_current_user

from agents.feedback.schemas.analytics import AnalyticsOverview, AspectSummary, SentimentBreakdown
from agents.feedback.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["feedback"])


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """Dashboard analytics are staff-only - a guest shouldn't be able to
    see aggregate sentiment/complaint data about a hotel, only their own
    reviews. Mirrors the "any non-guest role counts as staff" rule used
    by the reservation vertical's require_staff dependency."""
    if current_user.role == "guest":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required"
        )
    return current_user


@router.get("/sentiment", response_model=SentimentBreakdown)
def get_sentiment_breakdown(
    hotel_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    return analytics_service.compute_sentiment_breakdown(db, hotel_id=hotel_id)


@router.get("/aspects", response_model=List[AspectSummary])
def get_aspect_summary(
    hotel_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Full per-aspect breakdown (not just the top N in /overview) - for
    a dashboard table view."""
    return analytics_service.compute_aspect_summary(db, hotel_id=hotel_id)


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    hotel_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """The main hotel-management dashboard payload: sentiment breakdown,
    top positive/negative aspects, and a generated summary."""
    return analytics_service.generate_overview(db, hotel_id=hotel_id)
