from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.review import Review, ReviewAspect

from agents.feedback.schemas.analytics import (
    AnalyticsOverview,
    AspectSummary,
    SentimentBreakdown,
)

# Number of top positive/negative aspects to surface on the dashboard.
_TOP_N_ASPECTS = 3


def compute_sentiment_breakdown(
    db: Session, hotel_id: Optional[int] = None
) -> SentimentBreakdown:
    """Count reviews by overall_sentiment (positive/neutral/negative/mixed)
    and turn those counts into percentages."""
    query = db.query(Review.overall_sentiment, func.count(Review.id))
    if hotel_id is not None:
        query = query.filter(Review.hotel_id == hotel_id)
    counts = dict(query.group_by(Review.overall_sentiment).all())

    total = sum(counts.values())

    def pct(n: int) -> float:
        return round((n / total) * 100, 1) if total else 0.0

    positive = counts.get("positive", 0)
    neutral = counts.get("neutral", 0)
    negative = counts.get("negative", 0)
    mixed = counts.get("mixed", 0)

    return SentimentBreakdown(
        total=total,
        positive=positive,
        neutral=neutral,
        negative=negative,
        mixed=mixed,
        positive_pct=pct(positive),
        neutral_pct=pct(neutral),
        negative_pct=pct(negative),
        mixed_pct=pct(mixed),
    )


def compute_aspect_summary(
    db: Session, hotel_id: Optional[int] = None
) -> List[AspectSummary]:
    """Tally each aspect's clause-level sentiment across all matching
    reviews. ReviewAspect.sentiment is always positive/negative/neutral
    (never "mixed" - that label only applies at the whole-review level),
    so net_score = positive_count - negative_count is a clean "how do
    guests feel about X overall" ranking signal."""
    query = db.query(ReviewAspect.aspect, ReviewAspect.sentiment, func.count(ReviewAspect.id))
    if hotel_id is not None:
        query = query.join(Review, Review.id == ReviewAspect.review_id).filter(
            Review.hotel_id == hotel_id
        )
    rows = query.group_by(ReviewAspect.aspect, ReviewAspect.sentiment).all()

    tally: Dict[str, Dict[str, int]] = {}
    for aspect, sentiment, count in rows:
        counts = tally.setdefault(aspect, {"positive": 0, "negative": 0, "neutral": 0})
        if sentiment in counts:
            counts[sentiment] = count

    return [
        AspectSummary(
            aspect=aspect,
            positive_count=counts["positive"],
            negative_count=counts["negative"],
            neutral_count=counts["neutral"],
            net_score=counts["positive"] - counts["negative"],
        )
        for aspect, counts in tally.items()
    ]


def build_summary_text(
    breakdown: SentimentBreakdown, aspects: List[AspectSummary]
) -> str:
    """Template-based natural-language summary - no LLM involved, matching
    the project spec's own example output style (e.g. "Most positive
    aspect: Location. Most negative aspect: Breakfast service.")."""
    if breakdown.total == 0:
        return "No reviews yet."

    positive_aspects = sorted(
        (a for a in aspects if a.net_score > 0), key=lambda a: a.net_score, reverse=True
    )
    negative_aspects = sorted(
        (a for a in aspects if a.net_score < 0), key=lambda a: a.net_score
    )

    parts = [
        f"{breakdown.positive_pct}% of reviews are positive and "
        f"{breakdown.negative_pct}% are negative"
        + (f" ({breakdown.mixed_pct}% mixed)" if breakdown.mixed else "")
        + "."
    ]
    if positive_aspects:
        parts.append(f"Guests most frequently praised {positive_aspects[0].aspect}.")
    if negative_aspects:
        parts.append(f"The most common complaints concerned {negative_aspects[0].aspect}.")
    if not positive_aspects and not negative_aspects:
        parts.append("No clear aspect-level trends yet.")

    return " ".join(parts)


def generate_overview(
    db: Session, hotel_id: Optional[int] = None
) -> AnalyticsOverview:
    """The full hotel-management dashboard payload: sentiment breakdown,
    top positive/negative aspects, and a generated summary."""
    breakdown = compute_sentiment_breakdown(db, hotel_id=hotel_id)
    aspects = compute_aspect_summary(db, hotel_id=hotel_id)

    rating_query = db.query(func.avg(Review.rating))
    if hotel_id is not None:
        rating_query = rating_query.filter(Review.hotel_id == hotel_id)
    average_rating = rating_query.scalar()

    top_positive = sorted(
        (a for a in aspects if a.net_score > 0), key=lambda a: a.net_score, reverse=True
    )[:_TOP_N_ASPECTS]
    top_negative = sorted(
        (a for a in aspects if a.net_score < 0), key=lambda a: a.net_score
    )[:_TOP_N_ASPECTS]

    return AnalyticsOverview(
        hotel_id=hotel_id,
        total_reviews=breakdown.total,
        average_rating=round(float(average_rating), 2) if average_rating is not None else None,
        sentiment_breakdown=breakdown,
        top_positive_aspects=top_positive,
        top_negative_aspects=top_negative,
        summary_text=build_summary_text(breakdown, aspects),
    )
