from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from agents.feedback.services import analytics_service


def get_sentiment_breakdown(db: Session, hotel_id: Optional[int] = None) -> Dict[str, Any]:
    """Tool: sentiment counts/percentages, optionally scoped to one hotel."""
    breakdown = analytics_service.compute_sentiment_breakdown(db, hotel_id=hotel_id)
    return {"success": True, "data": breakdown.model_dump()}


def get_aspect_summary(db: Session, hotel_id: Optional[int] = None) -> Dict[str, Any]:
    """Tool: per-aspect positive/negative/neutral tally, optionally scoped
    to one hotel."""
    aspects = analytics_service.compute_aspect_summary(db, hotel_id=hotel_id)
    return {"success": True, "data": {"aspects": [a.model_dump() for a in aspects]}}


def get_analytics_overview(db: Session, hotel_id: Optional[int] = None) -> Dict[str, Any]:
    """Tool: the full dashboard payload - sentiment breakdown, top
    positive/negative aspects, and a generated summary."""
    overview = analytics_service.generate_overview(db, hotel_id=hotel_id)
    return {"success": True, "data": overview.model_dump()}
