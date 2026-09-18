"""Hybrid Information Retrieval for the Recommendation Agent.

Pipeline: metadata filtering (SQL) -> hybrid scoring (keyword + semantic)
-> fusion + rating tie-break -> ranking -> grounded explanation.

Filtering happens BEFORE ranking (structured filters like "in Colombo"
are hard constraints, not soft preferences) — see docs/agents/
recommendation.md for the full reasoning.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.place import Place

from agents.recommendation.schemas.places import (
    PlaceOut,
    PlaceSearchRequest,
    PlaceSearchResult,
)
from agents.recommendation.services import explanation_service

KEYWORD_WEIGHT = 0.4
SEMANTIC_WEIGHT = 0.5
RATING_WEIGHT = 0.1
SEMANTIC_MATCH_THRESHOLD = 0.45


def _tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-zA-Z']+", text.lower()) if len(w) > 2]


def _rating_norm(rating: Optional[Decimal]) -> float:
    if rating is None:
        return 0.0
    return float(rating) / 5.0


def _keyword_score(query_tokens: List[str], place: Place) -> float:
    if not query_tokens:
        return 0.0
    haystack = " ".join(
        filter(None, [place.name, place.description, place.cuisine, place.tags])
    ).lower()
    hits = sum(1 for token in query_tokens if token in haystack)
    return hits / len(query_tokens)


class PlaceEmbeddingRanker:
    """FastEmbed + FAISS semantic ranker, scoped to one candidate set per
    call — rebuilds a tiny in-memory index per request, which is cheap at
    demo scale (tens of places)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding
            except (ImportError, OSError, RuntimeError) as exc:
                raise RuntimeError(
                    "Semantic search is unavailable in this environment "
                    "(fastembed/faiss not installed or failed to load)."
                ) from exc
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def rank(self, query: str, places: List[Place]) -> Dict[int, float]:
        if not query.strip() or not places:
            return {}

        try:
            import faiss
            import numpy as np
        except (ImportError, OSError, RuntimeError) as exc:
            raise RuntimeError(
                "Semantic search is unavailable in this environment "
                "(fastembed/faiss not installed or failed to load)."
            ) from exc

        model = self._get_model()
        texts = [f"{p.name}. {p.description}" for p in places]

        def _encode(items: List[str]):
            vectors = np.asarray(list(model.embed(items)), dtype="float32")
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            return vectors / np.maximum(norms, 1e-12)

        place_vectors = _encode(texts)
        index = faiss.IndexFlatIP(place_vectors.shape[1])
        index.add(place_vectors)

        query_vector = _encode([query])
        scores, indexes = index.search(query_vector, len(places))

        return {
            places[idx].id: float(score)
            for score, idx in zip(scores[0], indexes[0])
            if idx >= 0
        }


def _matched_on(request, place, keyword_score, semantic_score) -> List[str]:
    matched: List[str] = []
    if request.city:
        matched.append("city")
    if request.category:
        matched.append("category")
    if request.cuisine:
        matched.append("cuisine")
    if request.budget_tier:
        matched.append("budget_tier")
    if keyword_score > 0:
        matched.append("keyword match")
    if semantic_score >= SEMANTIC_MATCH_THRESHOLD:
        matched.append("semantic similarity")
    return matched


def _apply_metadata_filters(db: Session, request: PlaceSearchRequest) -> List[Place]:
    query = db.query(Place).filter(Place.is_active.is_(True))
    if request.city:
        query = query.filter(Place.city.ilike(request.city))
    if request.category:
        query = query.filter(Place.category == request.category.value)
    if request.cuisine:
        query = query.filter(Place.cuisine.ilike(f"%{request.cuisine}%"))
    if request.budget_tier:
        query = query.filter(Place.budget_tier == request.budget_tier.value)
    return query.all()


def search_places(
    db: Session,
    request: PlaceSearchRequest,
    ranker: Optional[PlaceEmbeddingRanker] = None,
) -> List[PlaceSearchResult]:
    candidates = _apply_metadata_filters(db, request)
    if not candidates:
        return []

    query_text = (request.query or "").strip()
    query_tokens = _tokenize(query_text)

    semantic_scores: Dict[int, float] = {}
    if query_text:
        ranker = ranker or PlaceEmbeddingRanker()
        try:
            semantic_scores = ranker.rank(query_text, candidates)
        except RuntimeError:
            semantic_scores = {}  # graceful degradation

    scored: List[tuple] = []
    for place in candidates:
        keyword_score = _keyword_score(query_tokens, place)
        semantic_score = semantic_scores.get(place.id, 0.0)
        final_score = (
            KEYWORD_WEIGHT * keyword_score
            + SEMANTIC_WEIGHT * semantic_score
            + RATING_WEIGHT * _rating_norm(place.rating)
        )
        scored.append((place, keyword_score, semantic_score, final_score))

    scored.sort(key=lambda row: (row[3], _rating_norm(row[0].rating)), reverse=True)

    results: List[PlaceSearchResult] = []
    for place, keyword_score, semantic_score, final_score in scored[: request.max_results]:
        matched_on = _matched_on(request, place, keyword_score, semantic_score)
        explanation = explanation_service.build_explanation(
            request, place, matched_on, use_llm=request.use_llm_explanation
        )
        results.append(
            PlaceSearchResult(
                place=PlaceOut.model_validate(place),
                score=round(final_score, 4),
                keyword_score=round(keyword_score, 4),
                semantic_score=round(semantic_score, 4),
                matched_on=matched_on,
                explanation=explanation,
            )
        )
    return results