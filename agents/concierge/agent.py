from typing import Any, Dict, Optional, Union

from app.schemas.a2a import A2AResponse
from agents.common.base_agent import BaseAgent
from agents.concierge.services.entities import extract_entities
from agents.concierge.services.rag import answer_faq
from agents.reservation.agent import reservation_agent
from agents.reservation.agent_context import ReservationContext


class ConciergeAgent(BaseAgent):
    _INTENT_KEYWORDS = {
        "Reservation": (
            "book",
            "booking",
            "reserve",
            "reservation",
            "availability",
            "cancel",
        ),
        "Recommendation": (
            "recommend",
            "recommendation",
            "suggest",
            "restaurant",
            "attraction",
            "activity",
        ),
        "Feedback": (
            "feedback",
            "review",
            "complaint",
            "problem",
            "issue",
        ),
    }

    def __init__(self, message: Optional[str] = None):
        super().__init__("concierge")
        self.message = message

    def classify_intent(self, message: Optional[str] = None) -> str:
        message = message if message is not None else self.message
        if not message:
            return "FAQ"

        normalized_message = message.lower()
        if (
            ("cancellation" in normalized_message or "cancel" in normalized_message)
            and any(term in normalized_message for term in ("policy", "fee", "charge", "refund"))
        ):
            return "FAQ"
        for intent, keywords in self._INTENT_KEYWORDS.items():
            if any(keyword in normalized_message for keyword in keywords):
                return intent
        return "FAQ"

    def prepare_delegation_payload(
        self, message: Optional[str] = None
    ) -> Dict[str, Any]:
        message = message if message is not None else self.message
        if not message:
            raise ValueError("A message is required to prepare a delegation payload")

        intent = self.classify_intent(message)
        return {
            "agent": intent.lower(),
            "intent": intent,
            "message": message,
        }

    async def handle_message(
        self,
        context: Optional[ReservationContext],
        message: Union[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Classify a request and delegate reservation work in-process.

        A reservation request may include a structured ``payload`` and an
        operation (for example ``create_booking``). Free text is still
        classified, but cannot be turned into a booking without those
        validated parameters.
        """
        text = message if isinstance(message, str) else message.get("message", "")
        self.message = text
        intent = self.classify_intent(text)
        entities = extract_entities(text)

        if intent != "Reservation":
            if intent == "FAQ":
                faq = answer_faq(text)
                return A2AResponse(
                    status="success",
                    agent=self.name,
                    data={
                        "intent": intent,
                        "message": text,
                        "entities": entities,
                        "answer": faq["answer"],
                        "sources": faq["sources"],
                        **({"error": faq["error"]} if faq.get("error") else {}),
                    },
                ).model_dump()
            return A2AResponse(
                status="success",
                agent=self.name,
                data={"intent": intent, "message": text, "entities": entities},
            ).model_dump()

        if context is None:
            return self._error_response(
                "Reservation requests require an authenticated reservation context"
            ).model_dump()

        request = message if isinstance(message, dict) else {}
        payload = dict(request.get("payload") or {})
        for key, value in entities.items():
            payload.setdefault(key, value)
        operation = request.get("operation") or payload.pop("operation", None)
        operation = operation or "create_booking"
        if (
            operation == "create_booking"
            and "room_id" not in payload
            and all(key in payload for key in ("room_type", "check_in_date", "check_out_date", "guests"))
        ):
            search_result = await reservation_agent.handle_message(
                context,
                {"intent": "search_rooms", "payload": {
                    key: payload[key]
                    for key in ("room_type", "check_in_date", "check_out_date", "guests")
                }},
            )
            rooms = search_result.get("data", {}).get("rooms", [])
            if len(rooms) != 1:
                message = (
                    "I found no available matching rooms."
                    if not rooms
                    else "I found multiple matching rooms. Please choose a room before I confirm the booking."
                )
                return self._error_response(message).model_dump()
            payload["room_id"] = rooms[0]["room"]["id"]
        if operation == "create_booking":
            payload.pop("room_type", None)
        delegation = {"intent": operation, "payload": payload}

        try:
            reservation_result = await reservation_agent.handle_message(
                context, delegation
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            return self._error_response(
                f"Reservation could not be completed: {exc}"
            ).model_dump()

        if reservation_result.get("status") != "success":
            return self._error_response(
                reservation_result.get("error")
                or "Reservation could not be completed"
            ).model_dump()

        return A2AResponse(
            status="success",
            agent=self.name,
            data={
                "intent": intent,
                "entities": entities,
                "delegated_to": reservation_agent.name,
                "operation": operation,
                "result": reservation_result.get("data", {}),
            },
        ).model_dump()

    def _error_response(self, message: str) -> A2AResponse:
        return A2AResponse(status="error", agent=self.name, data={}, error=message)


concierge_agent = ConciergeAgent()
