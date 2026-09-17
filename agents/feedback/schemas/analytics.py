from typing import List, Optional

from pydantic import BaseModel


class SentimentBreakdown(BaseModel):
    """Counts and percentages of overall_sentiment across a set of reviews."""

    total: int
    positive: int
    neutral: int
    negative: int
    mixed: int
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    mixed_pct: float


class AspectSummary(BaseModel):
    """One aspect's sentiment tally across a set of reviews, e.g. how many
    times "breakfast" was mentioned positively vs negatively."""

    aspect: str
    positive_count: int
    negative_count: int
    neutral_count: int
    net_score: int  # positive_count - negative_count; used for ranking


class AnalyticsOverview(BaseModel):
    """The full hotel-management dashboard payload for one hotel (or the
    whole platform, when hotel_id is not filtered)."""

    hotel_id: Optional[int]
    total_reviews: int
    average_rating: Optional[float]
    sentiment_breakdown: SentimentBreakdown
    top_positive_aspects: List[AspectSummary]
    top_negative_aspects: List[AspectSummary]
    summary_text: str
