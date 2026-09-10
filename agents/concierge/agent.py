from typing import Any, Dict, Optional

from agents.common.base_agent import BaseAgent


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

    async def handle_message(self, context: Any, message: str) -> Dict[str, Any]:
        self.message = message
        return self.prepare_delegation_payload()


concierge_agent = ConciergeAgent()
