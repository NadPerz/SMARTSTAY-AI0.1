"""Small, dependency-free NLP for the Recommendation Agent. Mirrors the
style of agents/concierge/services/entities.py (regex/keyword-based, no
model load)."""

from __future__ import annotations

import re
from typing import Any, Dict, List

_CATEGORY_KEYWORDS: Dict[str, tuple] = {
    "restaurant": ("restaurant", "food", "eat", "dining", "dine", "cafe", "coffee", "bakery", "meal"),
    "attraction": ("attraction", "sight", "sightseeing", "temple", "museum", "landmark", "monument", "fort", "beach", "viewpoint"),
    "activity": ("activity", "activities", "tour", "adventure", "hike", "hiking", "safari", "trek", "trekking", "diving", "surfing", "cycling"),
    "shopping": ("shopping", "shop", "mall", "market", "souvenir", "boutique"),
    "entertainment": ("entertainment", "nightlife", "bar", "club", "live music", "casino", "show"),
}

_CUISINE_KEYWORDS = (
    "seafood", "italian", "chinese", "indian", "sri lankan", "srilankan",
    "local", "japanese", "sushi", "thai", "vegetarian", "vegan", "western",
    "continental", "bbq", "barbecue", "street food", "fine dining", "cafe",
)

_BUDGET_KEYWORDS: Dict[str, tuple] = {
    "budget": ("cheap", "affordable", "budget", "inexpensive", "low-cost", "low cost"),
    "moderate": ("moderate", "mid-range", "mid range", "reasonable"),
    "premium": ("expensive", "luxury", "luxurious", "premium", "upscale", "fine dining", "high-end", "high end"),
}

_KNOWN_CITIES = ("colombo", "kandy", "galle", "ella", "negombo")

_STOPWORDS = {
    "a", "an", "the", "for", "to", "of", "in", "near", "nearby", "close",
    "with", "and", "or", "is", "are", "we", "i", "my", "me", "please",
    "find", "recommend", "suggest", "some", "good", "want", "would",
    "like", "us", "our", "that",
}

_PROXIMITY_WORDS = ("nearby", "near", "close by", "close to", "walking distance")


def _find_category(lowered: str) -> str | None:
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return None


def _find_cuisine(lowered: str) -> str | None:
    for cuisine in _CUISINE_KEYWORDS:
        if cuisine in lowered:
            return "sri lankan" if cuisine == "srilankan" else cuisine
    return None


def _find_budget_tier(lowered: str) -> str | None:
    for tier, keywords in _BUDGET_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return tier
    return None


def _find_city(lowered: str) -> str | None:
    for city in _KNOWN_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", lowered):
            return city.title()
    return None


def _keywords(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def extract_recommendation_entities(text: str) -> Dict[str, Any]:
    """Extract structured recommendation filters from a free-text guest
    message. Missing values are omitted (never guessed)."""
    if not text or not isinstance(text, str):
        return {}

    lowered = text.lower()
    result: Dict[str, Any] = {}

    category = _find_category(lowered)
    if category:
        result["category"] = category

    cuisine = _find_cuisine(lowered)
    if cuisine:
        result["cuisine"] = cuisine

    budget_tier = _find_budget_tier(lowered)
    if budget_tier:
        result["budget_tier"] = budget_tier

    city = _find_city(lowered)
    if city:
        result["city"] = city

    if any(phrase in lowered for phrase in _PROXIMITY_WORDS):
        result["near_hotel"] = True

    keywords = _keywords(text)
    if keywords:
        result["keywords"] = keywords

    return result