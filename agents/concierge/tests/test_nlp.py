from agents.concierge.services.entities import extract_entities
from agents.concierge.services.rag import PolicyRetriever, chunk_document
from agents.concierge.services.rag import answer_faq
from agents.concierge.agent import ConciergeAgent
from agents.reservation.agent_context import ReservationContext
import asyncio


def test_extracts_booking_entities():
    entities = extract_entities(
        "I'd like a king room for 2 adults from June 12 to June 15"
    )

    assert entities["check_in_date"].endswith("-06-12")
    assert entities["check_out_date"].endswith("-06-15")
    assert entities["guests"] == 2
    assert entities["room_type"] == "king"


def test_chunk_document_overlaps_without_empty_chunks():
    chunks = chunk_document("one two three four five six", "policy.md", 4, 1)

    assert [chunk["source"] for chunk in chunks] == ["policy.md"] * 2
    assert chunks[0]["text"] == "one two three four"
    assert chunks[1]["text"] == "four five six"


def test_policy_retriever_has_six_source_documents():
    retriever = PolicyRetriever()

    assert len(
        [path for path in retriever.documents_dir.glob("*.md") if path.name != "README.md"]
    ) == 6


def test_faq_response_uses_retrieved_policy(monkeypatch):
    monkeypatch.setattr(
        "agents.concierge.agent.answer_faq",
        lambda query: {
            "answer": "Check-in begins at 3:00 PM.",
            "sources": ["check-in-and-check-out.md"],
        },
    )

    import asyncio

    response = asyncio.run(ConciergeAgent().handle_message(None, "What time is check-in?"))

    assert response["data"]["answer"] == "Check-in begins at 3:00 PM."
    assert response["data"]["sources"] == ["check-in-and-check-out.md"]


def test_rag_model_load_failure_returns_verification_fallback(monkeypatch):
    retriever = PolicyRetriever()
    monkeypatch.setattr(
        retriever,
        "retrieve",
        lambda query, top_k=3: (_ for _ in ()).throw(
            RuntimeError("embedding backend was unavailable")
        ),
    )

    response = answer_faq("What time is check-in?", retriever=retriever)

    assert response["sources"] == []
    assert "can't verify" in response["answer"]
    assert "embedding backend" in response["error"]


def test_unsupported_pool_and_shuttle_question_returns_fallback():
    response = answer_faq(
        "Does the hotel have a swimming pool and airport shuttle?"
    )

    assert response["answer"] == "I can't verify that from the hotel policies."
    assert response["sources"] == []


def test_supported_breakfast_question_returns_breakfast_policy():
    response = answer_faq(
        "What time is breakfast served and is it included?"
    )

    assert response["sources"] == ["breakfast-policy.md"]
    assert "6:30 AM" in response["answer"]


def test_supported_check_in_question_returns_only_check_in_policy():
    response = answer_faq("What time is check-in and check-out?")

    assert response["sources"] == ["check-in-and-check-out.md"]
    assert "3:00 PM" in response["answer"]


def test_explicit_cancel_operation_overrides_policy_words(monkeypatch):
    delegated = {}

    async def fake_handle(context, request):
        delegated.update(request)
        return {"status": "success", "data": {"cancelled": True}}

    monkeypatch.setattr(
        "agents.concierge.agent.reservation_agent.handle_message", fake_handle
    )
    response = asyncio.run(
        ConciergeAgent().handle_message(
            ReservationContext(db=None, current_user=object()),
            {
                "message": "Cancel my booking and refund the charge",
                "operation": "cancel_booking",
                "payload": {"booking_id": 1, "confirm": True},
            },
        )
    )

    assert response["status"] == "success"
    assert delegated["intent"] == "cancel_booking"


def test_room_search_failure_is_returned_to_guest(monkeypatch):
    async def failed_search(context, request):
        return {"status": "error", "data": {}, "error": "search unavailable"}

    monkeypatch.setattr(
        "agents.concierge.agent.reservation_agent.handle_message", failed_search
    )
    response = asyncio.run(
        ConciergeAgent().handle_message(
            ReservationContext(db=None, current_user=object()),
            "Book a king room for 2 guests from October 6 to October 9",
        )
    )

    assert response["status"] == "error"
    assert response["error"] == "search unavailable"


def test_room_availability_message_delegates_to_search_rooms(monkeypatch):
    delegated = {}

    async def search_rooms(context, request):
        delegated.update(request)
        return {"status": "success", "data": {"count": 1, "rooms": []}}

    monkeypatch.setattr(
        "agents.concierge.agent.reservation_agent.handle_message", search_rooms
    )
    response = asyncio.run(
        ConciergeAgent().handle_message(
            ReservationContext(db=None, current_user=object()),
            "Find available deluxe rooms for 2 guests from December 1 to December 4, 2026",
        )
    )

    assert response["status"] == "success"
    assert response["data"]["intent"] == "Reservation"
    assert delegated["intent"] == "search_rooms"
    assert delegated["payload"] == {
        "room_type": "deluxe",
        "check_in_date": "2026-12-01",
        "check_out_date": "2026-12-04",
        "guests": 2,
    }


def test_find_restaurant_is_not_room_search():
    assert ConciergeAgent().classify_intent("Find a restaurant") == "Recommendation"
