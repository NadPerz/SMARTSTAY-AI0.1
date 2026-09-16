import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from app.schemas.a2a import A2ARequest, A2AResponse

from agents.common.base_agent import BaseAgent
from agents.feedback.agent_context import FeedbackContext
from agents.feedback.tools import review_tools


class FeedbackAgent(BaseAgent):
    """Owns the guest feedback vertical: submitting reviews and reading
    them back, with sentiment/aspect extraction applied automatically at
    submission time.

    Structured exactly like ReservationAgent (agents/reservation/agent.py)
    on purpose — a name -> (tool, needs_user) dispatch table, and
    handle_message()/handle_task() returning the shared A2AResponse shape
    (status/agent/data/error) — so Concierge (or any other caller) can
    integrate with this agent using the same pattern already used for
    Reservation, without a different response shape to special-case.

    Like ReservationAgent, this agent does not parse free-text guest
    messages itself; it expects a structured {intent, payload} task.
    """

    def __init__(self) -> None:
        super().__init__("feedback")

    # intent name -> (tool function, whether it requires an authenticated user)
    _TOOL_MAP: Dict[str, Tuple[Callable[..., Dict[str, Any]], bool]] = {
        "submit_review": (review_tools.submit_review, True),
        "get_review": (review_tools.get_review, False),
        "list_reviews": (review_tools.list_reviews, False),
    }

    async def handle_message(
        self,
        context: Optional[FeedbackContext],
        message: Union[str, Dict[str, Any], A2ARequest],
    ) -> Dict[str, Any]:
        """Entry point required by BaseAgent. `message` must be a
        structured task — a dict with intent/payload keys, or an
        A2ARequest instance. Returns a plain dict
        (A2AResponse.model_dump()) so the caller doesn't need to import
        the schema just to read the result — e.g. Concierge can call
        `await feedback_agent.handle_message(ctx, {"intent": "submit_review",
        "payload": {"rating": 4, "review_text": "..."}})` and read
        `result["status"]`/`result["data"]` directly.
        """
        if context is None or not isinstance(context, FeedbackContext):
            return self._error_response(
                "Feedback agent requires a FeedbackContext (db + current_user)"
            ).model_dump()

        if isinstance(message, str):
            return self._error_response(
                "Feedback agent expects a structured {intent, payload} task, "
                "not free text. Free-text understanding belongs to the "
                "Concierge/NLU layer."
            ).model_dump()

        intent, payload = self._normalize_task(message)
        return self.handle_task(context, intent, payload).model_dump()

    def handle_task(
        self, context: FeedbackContext, intent: str, payload: Dict[str, Any]
    ) -> A2AResponse:
        """The real dispatcher: structured intent + payload -> tool call ->
        A2AResponse. What Concierge (once wired) or tests should call
        directly."""
        entry = self._TOOL_MAP.get(intent)
        if entry is None:
            return self._error_response(f"Unknown feedback intent: {intent!r}")

        tool_fn, needs_user = entry
        if needs_user and context.current_user is None:
            return self._error_response("This action requires an authenticated user")

        kwargs: Dict[str, Any] = dict(payload)
        kwargs["db"] = context.db
        if needs_user:
            kwargs["current_user"] = context.current_user

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
    def _normalize_task(
        message: Union[Dict[str, Any], A2ARequest]
    ) -> Tuple[str, Dict[str, Any]]:
        if isinstance(message, A2ARequest):
            # Deliberately ignore message.user_id — context.current_user is
            # always the source of truth for who is making the request.
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


feedback_agent = FeedbackAgent()
