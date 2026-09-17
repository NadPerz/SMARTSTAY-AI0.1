from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    """What a guest submits. Sentiment fields are never accepted from the
    client — they're always derived server-side by the NLP engine."""

    hotel_id: Optional[int] = Field(default=None, ge=1)
    rating: int = Field(ge=1, le=5)
    review_text: str = Field(min_length=1, max_length=5000)


class AspectSentimentOut(BaseModel):
    """One (aspect, sentiment) pair extracted from a review's text, with
    the clause it was derived from kept as supporting evidence."""

    aspect: str
    sentiment: str
    confidence: float
    snippet: str

    model_config = {"from_attributes": True}


class ReviewOut(BaseModel):
    """A stored Review as returned to API clients, including its
    server-computed sentiment and per-aspect breakdown."""

    id: int
    user_id: int
    hotel_id: Optional[int]
    rating: int
    review_text: str
    overall_sentiment: Optional[str]
    sentiment_score: Optional[float]
    created_at: datetime
    aspects: List[AspectSentimentOut] = []

    model_config = {"from_attributes": True}
