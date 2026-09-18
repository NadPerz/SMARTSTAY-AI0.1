import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from app.schemas.a2a import A2ARequest, A2AResponse

from agents.common.base_agent import BaseAgent
from agents.recommendation.agent_context import RecommendationContext
from agents.recommendation.services.nlp_service import extract_recommendation_entities
from agents.recommendation.tools import recommendation_tools

_ENTITY_TO_FILTER_KEYS = ("category", "cuisine", "budget_tier", "city")


class RecommendationAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("recommendation")

    _TOOL_MAP: Dict[str, Tuple[Callable[..., Dict[str, Any]], bool]] = {
        "search_recommendations": (recommendation_tools.search_recommendations, False),
        "get_place_details": (recommendation_tools.get_place_details, False),
    }

    async def handle_message(
        self,
        context: Optional[RecommendationContext],
        message: Union[str, Dict[str, Any], A2ARequest],
    ) -> Dict[str, Any]:
        if context is None or not isinstance(context, RecommendationContext):
            return self._error_response(
                "Recommendation agent requires a RecommendationContext (db + optional current_user)"
            ).model_dump()

        if isinstance(message, str):
            intent, payload = "search_recommendations", self._payload_from_text(message)
        else:
            intent, payload = self._normalize_task(message)

        return self.handle_task(context, intent, payload).model_dump()

    def handle_task(
        self, context: RecommendationContext, intent: str, payload: Dict[str, Any]
    ) -> A2AResponse:
        entry = self._TOOL_MAP.get(intent)
        if entry is None:
            return self._error_response(f"Unknown recommendation intent: {intent!r}")

        tool_fn, needs_user = entry
        kwargs: Dict[str, Any] = dict(payload)
        kwargs["db"] = context.db

        missing = self._missing_required_params(tool_fn, kwargs)
        if missing:
            return self._error_response(
                f"Missing required parameter(s) for '{intent}': {', '.join(missing)}"
            )

        result = tool_fn(**kwargs)
        return A2AResponse(
            status="success" if result.get("success") else "error",
            agent=self.name,
            data=result.get("data") or {},
            error=result.get("error"),
        )

    @staticmethod
    def _payload_from_text(message: str) -> Dict[str, Any]:
        entities = extract_recommendation_entities(message)
        payload: Dict[str, Any] = {"query": message}
        for key in _ENTITY_TO_FILTER_KEYS:
            if key in entities:
                payload[key] = entities[key]
        return payload

    @staticmethod
    def _normalize_task(
        message: Union[Dict[str, Any], A2ARequest]
    ) -> Tuple[str, Dict[str, Any]]:
        if isinstance(message, A2ARequest):
            return message.intent, dict(message.payload)
        intent = message.get("intent", "")
        payload = dict(message.get("payload") or {})
        return intent, payload

    @staticmethod
    def _missing_required_params(fn: Callable, kwargs: Dict[str, Any]) -> List[str]:
        sig = inspect.signature(fn)
        missing = []
        for name, param in sig.parameters.items():
            if param.default is inspect.Parameter.empty and name not in kwargs:
                missing.append(name)
        return missing

    def _error_response(self, message: str) -> A2AResponse:
        return A2AResponse(status="error", agent=self.name, data={}, error=message)


recommendation_agent = RecommendationAgent()