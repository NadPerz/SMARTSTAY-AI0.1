"""Catalog-composition analytics for the Recommendation Agent.

Deliberately scoped to what's derivable from the `places` table alone —
counts, distribution, ratings. It does NOT compute usage metrics (search
volume, click-through rate, recommendation relevance from real guest
interactions) because nothing in this codebase logs search/click events
yet. Faking those numbers would be worse than not having them; see
docs/agents/recommendation.md "Known gaps" for the honest status and what
a future SearchEvent/click-log table would need to look like.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.place import Place

from agents.recommendation.schemas.places import PlaceAnalyticsOverview


def build_overview(db: Session) -> PlaceAnalyticsOverview:
    places = db.query(Place).all()

    active = [p for p in places if p.is_active]
    inactive = [p for p in places if not p.is_active]

    by_category = Counter(p.category for p in places)
    by_city = Counter(p.city for p in places)
    by_budget_tier = Counter(p.budget_tier for p in places)

    rated = [float(p.rating) for p in places if p.rating is not None]
    average_rating: Optional[float] = round(sum(rated) / len(rated), 2) if rated else None

    average_rating_by_category: Dict[str, float] = {}
    for category in by_category:
        category_ratings = [
            float(p.rating) for p in places if p.category == category and p.rating is not None
        ]
        if category_ratings:
            average_rating_by_category[category] = round(
                sum(category_ratings) / len(category_ratings), 2
            )

    return PlaceAnalyticsOverview(
        total_places=len(places),
        active_places=len(active),
        inactive_places=len(inactive),
        by_category=dict(by_category),
        by_city=dict(by_city),
        by_budget_tier=dict(by_budget_tier),
        average_rating=average_rating,
        average_rating_by_category=average_rating_by_category,
    )