import asyncio
from datetime import date, timedelta

from app.models.booking import Booking
from app.schemas.a2a import A2ARequest

from agents.reservation.agent import reservation_agent
from agents.reservation.agent_context import ReservationContext

TODAY = date.today()


def _dates(offset_in=10, nights=3):
    check_in = (TODAY + timedelta(days=offset_in)).isoformat()
    check_out = (TODAY + timedelta(days=offset_in + nights)).isoformat()
    return check_in, check_out


def _run(coro):
    """Helper to run the agent's async handle_message from a plain sync
    test function, without adding a pytest-asyncio dependency."""
    return asyncio.run(coro)


def test_handle_message_requires_context(db_session):
    result = _run(
        reservation_agent.handle_message(None, {"intent": "search_rooms", "payload": {}})
    )
    assert result["status"] == "error"


def test_handle_message_rejects_free_text(db_session, guest):
    ctx = ReservationContext(db=db_session, current_user=guest)
    result = _run(reservation_agent.handle_message(ctx, "please book me a room"))
    assert result["status"] == "error"


def test_handle_task_unknown_intent(db_session, guest):
    ctx = ReservationContext(db=db_session, current_user=guest)
    result = _run(
        reservation_agent.handle_message(ctx, {"intent": "delete_everything", "payload": {}})
    )
    assert result["status"] == "error"


def test_handle_task_missing_required_params(db_session, guest):
    ctx = ReservationContext(db=db_session, current_user=guest)
    result = _run(
        reservation_agent.handle_message(
            ctx, {"intent": "search_rooms", "payload": {"guests": 2}}
        )
    )
    assert result["status"] == "error"
    assert "check_in_date" in result["error"]


def test_handle_task_search_rooms_dispatches_correctly(db_session, guest, room):
    check_in, check_out = _dates()
    ctx = ReservationContext(db=db_session, current_user=guest)
    result = _run(
        reservation_agent.handle_message(
            ctx,
            {
                "intent": "search_rooms",
                "payload": {
                    "check_in_date": check_in,
                    "check_out_date": check_out,
                    "guests": 2,
                },
            },
        )
    )
    assert result["status"] == "success"
    assert result["data"]["count"] == 1


def test_create_booking_requires_authenticated_context(db_session, room):
    check_in, check_out = _dates()
    anon_ctx = ReservationContext(db=db_session, current_user=None)
    result = _run(
        reservation_agent.handle_message(
            anon_ctx,
            {
                "intent": "create_booking",
                "payload": {
                    "room_id": room.id,
                    "check_in_date": check_in,
                    "check_out_date": check_out,
                    "guests": 2,
                    "confirm": True,
                },
            },
        )
    )
    assert result["status"] == "error"
    assert db_session.query(Booking).count() == 0


def test_spoofed_user_id_in_a2a_request_is_ignored(db_session, guest, other_guest, room):
    """The critical security test: even if a message claims to be acting on
    behalf of another user, the booking must be created under the actual
    authenticated context (ReservationContext.current_user), never the
    value carried inside the message."""
    check_in, check_out = _dates()
    ctx = ReservationContext(db=db_session, current_user=guest)

    spoofed_request = A2ARequest(
        user_id=str(other_guest.id),  # attacker-controlled, must be ignored
        intent="create_booking",
        payload={
            "room_id": room.id,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "guests": 2,
            "confirm": True,
        },
    )

    result = _run(reservation_agent.handle_message(ctx, spoofed_request))
    assert result["status"] == "success"

    created = db_session.query(Booking).filter(Booking.id == result["data"]["id"]).first()
    assert created.user_id == guest.id
    assert created.user_id != other_guest.id