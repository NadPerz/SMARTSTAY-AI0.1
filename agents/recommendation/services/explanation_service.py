"""Deterministic-by-default, grounded explanation generation, with
optional LLM polishing."""

from __future__ import annotations

from typing import List

from app.models.place import Place

from agents.recommendation.schemas.places import PlaceSearchRequest

_MATCH_PHRASES = {
    "city": "it's in the area you asked about",
    "category": "it matches the type of place you're looking for",
    "cuisine": "it matches your cuisine preference",
    "budget_tier": "it fits your budget",
    "keyword match": "it matches specific terms from your request",
    "semantic similarity": "it closely matches what you described",
}


def build_deterministic_explanation(
    request: PlaceSearchRequest, place: Place, matched_on: List[str]
) -> str:
    reasons = [_MATCH_PHRASES[key] for key in matched_on if key in _MATCH_PHRASES]
    if not reasons:
        reasons = ["it's a well-rated option in this category"]

    reason_text = "; ".join(reasons)
    rating_text = f" It's rated {place.rating}/5." if place.rating is not None else ""
    return f"Recommended because {reason_text}.{rating_text}"


def build_explanation(
    request: PlaceSearchRequest,
    place: Place,
    matched_on: List[str],
    use_llm: bool = False,
) -> str:
    deterministic = build_deterministic_explanation(request, place, matched_on)
    if not use_llm:
        return deterministic

    try:
        from app.services.llm_service import llm_service
    except ImportError:
        return deterministic

    system_prompt = (
        "You rewrite a short hotel-recommendation explanation to sound more "
        "natural. You MUST NOT add, invent, or imply any fact that is not "
        "explicitly given to you below. Do not mention prices, awards, or "
        "features that weren't stated. Keep it to one or two sentences."
    )
    user_prompt = (
        f"Place name: {place.name}\n"
        f"Category: {place.category}\n"
        f"Cuisine: {place.cuisine or 'n/a'}\n"
        f"Budget tier: {place.budget_tier}\n"
        f"Rating: {place.rating if place.rating is not None else 'n/a'}\n"
        f"Description: {place.description}\n"
        f"Reasons this matched the guest's request: {', '.join(matched_on) or 'general relevance'}\n\n"
        f"Base explanation to rewrite naturally: {deterministic}"
    )
    try:
        return llm_service.generate(system_prompt, user_prompt, max_tokens=120)
    except RuntimeError:
        return deterministic