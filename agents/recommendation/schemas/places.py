import enum
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlaceCategory(str, enum.Enum):
    RESTAURANT = "restaurant"
    ATTRACTION = "attraction"
    ACTIVITY = "activity"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"


class PlaceBudgetTier(str, enum.Enum):
    BUDGET = "budget"
    MODERATE = "moderate"
    PREMIUM = "premium"


def _split_tags(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [tag.strip() for tag in str(value).split(",") if tag.strip()]


class PlaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: PlaceCategory
    cuisine: Optional[str] = None
    city: str
    address: Optional[str] = None
    description: str
    budget_tier: PlaceBudgetTier
    rating: Optional[Decimal] = None
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value):
        return _split_tags(value)


class PlaceCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    category: PlaceCategory
    cuisine: Optional[str] = None
    city: str = Field(min_length=1)
    address: Optional[str] = None
    description: str = Field(min_length=1)
    budget_tier: PlaceBudgetTier
    rating: Optional[Decimal] = Field(default=None, ge=0, le=5)
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value):
        return _split_tags(value)

class PlaceUpdateRequest(BaseModel):
    """Admin-only: partial update of an existing place. Every field is
    optional — only the fields actually provided are changed (PATCH
    semantics, not PUT)."""

    name: Optional[str] = Field(default=None, min_length=1)
    category: Optional[PlaceCategory] = None
    cuisine: Optional[str] = None
    city: Optional[str] = Field(default=None, min_length=1)
    address: Optional[str] = None
    description: Optional[str] = Field(default=None, min_length=1)
    budget_tier: Optional[PlaceBudgetTier] = None
    rating: Optional[Decimal] = Field(default=None, ge=0, le=5)
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value):
        return None if value is None else _split_tags(value)

    def provided_fields(self) -> dict:
        return self.model_dump(exclude_unset=True, exclude_none=True)


class PlaceSearchRequest(BaseModel):
    query: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = None
    category: Optional[PlaceCategory] = None
    cuisine: Optional[str] = None
    budget_tier: Optional[PlaceBudgetTier] = None
    max_results: int = Field(default=5, ge=1, le=20)
    use_llm_explanation: bool = False

    def has_any_criteria(self) -> bool:
        return bool(
            (self.query and self.query.strip())
            or self.city
            or self.category
            or self.cuisine
            or self.budget_tier
        )


class PlaceSearchResult(BaseModel):
    place: PlaceOut
    score: float
    keyword_score: float
    semantic_score: float
    matched_on: List[str]
    explanation: str

class PlaceAnalyticsOverview(BaseModel):
    """Catalog-composition analytics for the admin dashboard (project
    brief section 22/23: "Recommendation usage" chart). Computed from the
    `places` table itself — does NOT include usage metrics like
    click-through rate, because that requires logging search/click
    events, which this agent does not do yet."""

    total_places: int
    active_places: int
    inactive_places: int
    by_category: dict
    by_city: dict
    by_budget_tier: dict
    average_rating: Optional[float] = None
    average_rating_by_category: dict = Field(default_factory=dict)