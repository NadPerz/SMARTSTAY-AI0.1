import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from app.schemas.a2a import A2ARequest, A2AResponse

from agents.common.base_agent import BaseAgent
from agents.reservation.agent_context import ReservationContext
from agents.reservation.tools import booking_tools, room_tools


class ReservationAgent(BaseAgent):
    """Owns the full reservation vertical: search, availability, booking
    creation/retrieval/modification/cancellation.

    This agent does NOT parse free-text guest messages. Natural-language
    understanding (turning "I need a room for two this weekend" into
    intent + extracted dates/guests) is Concierge/NLU territory and is not
    implemented anywhere in this codebase yet — it's tracked as future
    work, not faked here. ReservationAgent expects a STRUCTURED task: an
    intent name plus a payload of already-extracted parameters, using the
    team's shared A2ARequest/A2AResponse contract (app/schemas/a2a.py).
    This matches the architecture rule that agents communicate with
    structured messages, not raw natural language, between each other.

    The LLM (wherever it eventually sits, in Concierge) decides WHEN to
    call this agent and WITH WHAT intent/payload. This agent decides WHICH
    tool that maps to and calls it. The tool does the actual, deterministic
    work. The agent itself contains no business logic — that all lives in
    agents/reservation/services.
    """

    def __init__(self) -> None:
        super().__init__("reservation")

    # intent name -> (tool function, whether it requires an authenticated user)
    _TOOL_MAP: Dict[str, Tuple[Callable[..., Dict[str, Any]], bool]] = {
        "search_rooms": (room_tools.search_rooms, False),
        "check_availability": (room_tools.check_availability, False),
        "get_booking_summary": (booking_tools.get_booking_summary, False),
        "create_booking": (booking_tools.create_booking, True),
        "get_booking": (booking_tools.get_booking, True),
        "list_bookings": (booking_tools.list_my_bookings, True),
        "modify_booking": (booking_tools.modify_booking, True),
        "cancel_booking": (booking_tools.cancel_booking, True),
    }

    async def handle_message(
        self,
        context: Optional[ReservationContext],
        message: Union[str, Dict[str, Any], A2ARequest],
    ) -> Dict[str, Any]:
        """Entry point required by BaseAgent (so this agent is a drop-in
        peer of ConciergeAgent/etc). `message` must be a structured task —
        a dict with "intent"/"payload" keys, or an A2ARequest instance.

        A plain string is accepted but always returns a clear error: this
        layer intentionally does not attempt to parse free text (see class
        docstring). Returns a plain dict (A2AResponse.model_dump()) so the
        caller doesn't need to import the schema just to read the result.
        """
        if context is None or not isinstance(context, ReservationContext):
            return self._error_response(
                "Reservation agent requires a ReservationContext (db + current_user)"
            ).model_dump()

        if isinstance(message, str):
            return self._error_response(
                "Reservation agent expects a structured {intent, payload} task, "
                "not free text. Free-text understanding belongs to the "
                "Concierge/NLU layer (not yet implemented)."
            ).model_dump()

        intent, payload = self._normalize_task(message)
        return self.handle_task(context, intent, payload).model_dump()

    def handle_task(
        self, context: ReservationContext, intent: str, payload: Dict[str, Any]
    ) -> A2AResponse:
        """The real dispatcher: structured intent + payload -> tool call ->
        A2AResponse. This is what Concierge (once wired) or tests should
        call directly."""
        entry = self._TOOL_MAP.get(intent)
        if entry is None:
            return self._error_response(f"Unknown reservation intent: {intent!r}")

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
            # Deliberately ignore message.user_id here. The authenticated
            # context (ReservationContext.current_user) is always the
            # source of truth for who is making the request — never a
            # field carried inside a message payload, internal or not.
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


reservation_agent = ReservationAgent()