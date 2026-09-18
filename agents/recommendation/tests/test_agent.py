import asyncio

from app.schemas.a2a import A2ARequest

from agents.recommendation.agent import RecommendationAgent
from agents.recommendation.agent_context import RecommendationContext


def test_missing_context_returns_error(db_session):
    agent = RecommendationAgent()

    response = asyncio.run(agent.handle_message(None, "find me a restaurant"))

    assert response["status"] == "error"
    assert "RecommendationContext" in response["error"]


def test_structured_task_dispatches_to_search_tool(seeded_places, db_session):
    agent = RecommendationAgent()
    context = RecommendationContext(db=db_session)

    response = asyncio.run(
        agent.handle_message(
            context, {"intent": "search_recommendations", "payload": {"city": "Kandy"}}
        )
    )

    assert response["status"] == "success"
    assert response["data"]["count"] == 1
    assert response["data"]["results"][0]["place"]["name"] == "Temple of the Sacred Tooth Relic"


def test_a2a_request_is_dispatched_the_same_way(seeded_places, db_session):
    agent = RecommendationAgent()
    context = RecommendationContext(db=db_session)
    request = A2ARequest(
        user_id="irrelevant-here",
        intent="search_recommendations",
        payload={"city": "Kandy"},
    )

    response = asyncio.run(agent.handle_message(context, request))

    assert response["status"] == "success"
    assert response["data"]["count"] == 1


def test_unknown_intent_returns_error(db_session):
    agent = RecommendationAgent()
    context = RecommendationContext(db=db_session)

    response = asyncio.run(
        agent.handle_message(context, {"intent": "not_a_real_intent", "payload": {}})
    )

    assert response["status"] == "error"
    assert "Unknown recommendation intent" in response["error"]


def test_payload_from_text_maps_entities_to_filter_params():
    payload = RecommendationAgent._payload_from_text(
        "Find affordable seafood restaurants in Colombo"
    )

    assert payload["query"] == "Find affordable seafood restaurants in Colombo"
    assert payload["category"] == "restaurant"
    assert payload["cuisine"] == "seafood"
    assert payload["budget_tier"] == "budget"
    assert payload["city"] == "Colombo"


def test_free_text_message_dispatches_end_to_end(seeded_places, db_session, monkeypatch):
    class _StubRanker:
        def rank(self, query, places):
            return {p.id: 0.5 for p in places}

    monkeypatch.setattr(
        "agents.recommendation.services.retrieval_service.PlaceEmbeddingRanker",
        _StubRanker,
    )

    agent = RecommendationAgent()
    context = RecommendationContext(db=db_session)

    response = asyncio.run(
        agent.handle_message(context, "Find a seafood restaurant in Colombo")
    )

    assert response["status"] == "success"
    assert response["data"]["count"] >= 1
    assert response["data"]["results"][0]["place"]["name"] == "Ministry of Crab"