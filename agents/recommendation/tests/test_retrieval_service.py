from agents.recommendation.schemas.places import PlaceSearchRequest
from agents.recommendation.services import retrieval_service
from agents.recommendation.services.retrieval_service import PlaceEmbeddingRanker


class _StubRanker:
    """Returns fixed scores instead of loading a real embedding model."""

    def __init__(self, scores: dict):
        self._scores = scores

    def rank(self, query, places):
        return {p.id: self._scores.get(p.name, 0.0) for p in places}


class _BrokenRanker:
    def rank(self, query, places):
        raise RuntimeError("embedding backend unavailable")


def test_inactive_places_are_never_returned(seeded_places, db_session):
    request = PlaceSearchRequest(city="Colombo", category="restaurant")

    results = retrieval_service.search_places(db_session, request, ranker=_StubRanker({}))

    names = [r.place.name for r in results]
    assert "Closed Down Diner" not in names


def test_city_and_category_filters_narrow_candidates(seeded_places, db_session):
    request = PlaceSearchRequest(city="Kandy")

    results = retrieval_service.search_places(db_session, request, ranker=_StubRanker({}))

    assert len(results) == 1
    assert results[0].place.name == "Temple of the Sacred Tooth Relic"
    assert "city" in results[0].matched_on


def test_no_matching_candidates_returns_empty_list(seeded_places, db_session):
    request = PlaceSearchRequest(city="Nonexistent City")

    results = retrieval_service.search_places(db_session, request, ranker=_StubRanker({}))

    assert results == []


def test_semantic_score_influences_ranking(seeded_places, db_session):
    request = PlaceSearchRequest(
        city="Colombo", category="restaurant", query="somewhere fancy for a special occasion"
    )
    ranker = _StubRanker({"Ministry of Crab": 0.9, "Cafe Kumbuk": 0.2})

    results = retrieval_service.search_places(db_session, request, ranker=ranker)

    assert [r.place.name for r in results] == ["Ministry of Crab", "Cafe Kumbuk"]
    assert "semantic similarity" in results[0].matched_on


def test_keyword_match_is_detected_even_without_semantic_backend(seeded_places, db_session):
    request = PlaceSearchRequest(city="Colombo", category="restaurant", query="crab dishes")

    results = retrieval_service.search_places(db_session, request, ranker=_BrokenRanker())

    top = results[0]
    assert top.place.name == "Ministry of Crab"
    assert top.semantic_score == 0.0
    assert top.keyword_score > 0
    assert "keyword match" in top.matched_on


def test_degrades_gracefully_when_embedding_backend_unavailable(seeded_places, db_session):
    request = PlaceSearchRequest(city="Colombo", query="anything")

    results = retrieval_service.search_places(db_session, request, ranker=_BrokenRanker())

    assert len(results) == 2
    assert all(r.semantic_score == 0.0 for r in results)


def test_structured_filters_only_ranks_by_rating(seeded_places, db_session):
    request = PlaceSearchRequest(city="Colombo", category="restaurant")

    results = retrieval_service.search_places(db_session, request, ranker=_StubRanker({}))

    assert [r.place.name for r in results] == ["Ministry of Crab", "Cafe Kumbuk"]


def test_explanation_is_grounded_in_matched_filters(seeded_places, db_session):
    request = PlaceSearchRequest(city="Colombo", cuisine="seafood")

    results = retrieval_service.search_places(db_session, request, ranker=_StubRanker({}))

    explanation = results[0].explanation.lower()
    assert "cuisine" in explanation
    assert "budget" not in explanation


def test_real_ranker_class_raises_cleanly_on_empty_query():
    ranker = PlaceEmbeddingRanker()
    assert ranker.rank("", []) == {}
    assert ranker.rank("   ", [object()]) == {}  # type: ignore[list-item]