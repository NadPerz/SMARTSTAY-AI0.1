# Reservation Agent

Covers room search, availability checking,
booking creation/confirmation/retrieval/modification/cancellation, and the
backend/database layer those operations depend on.

## Architecture at a glance

```text
Guest / Concierge Agent
        │
        ▼
ReservationAgent.handle_task(context, intent, payload)
        │  (dispatches intent -> tool, using the shared
        │   A2ARequest/A2AResponse contract)
        ▼
agents/reservation/tools/*  (room_tools.py, booking_tools.py)
        │  (thin, deterministic wrappers — no business logic)
        ▼
agents/reservation/services/*  (availability_service.py, booking_service.py)
        │  (all real business logic: overlap checks, capacity,
        │   authorization, confirmation enforcement)
        ▼
backend/app/models/{room,booking}.py  (SQLAlchemy models)
        │
        ▼
PostgreSQL (source of truth)
```

The same service layer is used by two independent callers:

- **`backend/app/api/v1/bookings.py`** — the plain REST API, for the guest
  website/admin UI. Uses the Pydantic schemas directly (FastAPI already
  validates request bodies into them).
- **`agents/reservation/tools/*`** — the agent-facing interface, for the
  Concierge/AI chat flow. Takes primitive arguments (str dates, ints) since
  that's what an LLM tool call actually produces, and returns plain dicts.

Both sit on top of `availability_service.py` / `booking_service.py`, so
there's exactly one implementation of the rules that matter (double-booking,
capacity, confirmation) — not two copies that could drift apart.

## Files

| Layer | File | Purpose |
|---|---|---|
| Models | `backend/app/models/room.py` | Room inventory |
| | `backend/app/models/booking.py` | Bookings + `BookingStatus` enum |
| Schemas | `agents/reservation/schemas/rooms.py` | Search/output schemas |
| | `agents/reservation/schemas/bookings.py` | Booking request/response schemas |
| Services | `agents/reservation/services/availability_service.py` | Search, overlap check, single-room availability |
| | `agents/reservation/services/booking_service.py` | Create/get/list/modify/cancel |
| | `agents/reservation/services/exceptions.py` | Domain exceptions |
| Tools | `agents/reservation/tools/room_tools.py` | `search_rooms`, `check_availability` |
| | `agents/reservation/tools/booking_tools.py` | `get_booking_summary`, `create_booking`, `get_booking`, `list_my_bookings`, `modify_booking`, `cancel_booking` |
| Agent | `agents/reservation/agent.py` | `ReservationAgent` — intent dispatch |
| | `agents/reservation/agent_context.py` | `ReservationContext` (db + current_user) |
| API | `backend/app/api/v1/bookings.py` | REST endpoints |
| Data | `database/seeds/demo_fixtures/seed_rooms.py` | Idempotent demo rooms |
| Tests | `agents/reservation/tests/*`, `backend/app/tests/test_bookings_api.py` | 46 tests across all layers |

## Design decisions and viva talking points

**Why is `user_id` never accepted from client input?**
`CreateBookingRequest` has no `user_id` field at all — not "ignored if
present," structurally absent. The authenticated user's id is always read
server-side from `get_current_user` (REST) or `ReservationContext.current_user`
(agent). This prevents a guest from creating or viewing a booking under
someone else's account. `test_spoofed_user_id_in_a2a_request_is_ignored`
proves this holds even when an internal `A2ARequest` message explicitly
carries a different user's id in its `user_id` field — it's ignored, and
the booking is still attributed to the real authenticated user.

**Why two layers of double-booking protection?**
A DB-level `CheckConstraint` on `bookings` (`check_out_date > check_in_date`)
plus a `_nights`/`has_overlapping_booking` check enforced in
`availability_service.py`. Defense in depth: the app-level check gives a
clean error message; the DB constraint is a last-resort guard if application
logic ever has a bug. `has_overlapping_booking` is the single implementation
used by search, availability check, create, and modify — one function,
tested once (`test_has_overlapping_booking_*`), trusted everywhere.

**Why does `create_booking` re-check availability instead of trusting an
earlier search result?**
Race condition: two guests can see the same "available" room in search
results, then both try to book it. The re-check at write time (immediately
before the `INSERT`) means the second one gets a clear `RoomUnavailableError`
instead of a corrupted double-booking. `test_double_booking_returns_409`
and `test_create_booking_rejects_overlapping_dates` cover this.

**Why is the booking confirmation gate a boolean parameter (`confirm`),
not just a prompt instruction to the LLM?**
Because prompt instructions are not enforcement. `create_booking(confirm=False)`
has no code path that reaches the database write — the check happens before
any service call. An LLM could technically try to skip straight to
`create_booking` without ever calling `get_booking_summary` first; the
`confirm` gate is what actually stops the write in that case, not good
behavior on the LLM's part. Note this is different from the REST API,
where there's no `confirm` flag — the two-request flow itself
(`/bookings/summary` then `/bookings`) is the human-in-the-loop
confirmation, because a real UI enforces that ordering by construction.

**Why does the Reservation Agent refuse plain free-text messages?**
No LLM/NLP is integrated anywhere in this codebase yet — that's Concierge/
NLU work, tracked as future scope, not implemented. Rather than fake a
brittle regex-based parser and call it "understanding," `ReservationAgent.
handle_message` returns a clear, honest error for a raw string and expects
a structured `{intent, payload}` task instead (or an `A2ARequest`). This
is an honest architectural boundary, not a missing feature pretending to
be present.

**Why domain-specific exceptions (`RoomNotFoundError`, `RoomUnavailableError`,
etc.) instead of generic ones?**
Each maps to exactly one HTTP status in the API layer
(404/409/403/404 respectively) and one dict shape in the tools layer.
Callers can `except RoomUnavailableError` instead of parsing a string
message to figure out what went wrong.

**Why does the REST API and the agent tools layer both exist, if they call
the same service functions?**
They serve different callers with different natural input shapes. FastAPI
already parses a JSON body into a typed Pydantic schema for the REST routes
— passing that back out to primitives just to re-validate inside a tool
would be redundant. An LLM tool call, by contrast, produces raw
JSON-primitive arguments (strings, ints) with no schema of its own — the
tools layer is where that untrusted input gets validated into the same
schemas the REST layer already had for free.

## Known gaps (honest, not hidden)

- Concierge Agent doesn't call `ReservationAgent` yet — built and ready via
  `handle_task`, not wired up on the Concierge side yet (cross-team task).
- No admin endpoint to create/edit rooms (manual DB insert or the seed
  script only, for now).
- Dates must be ISO 8601 (`YYYY-MM-DD`) in every API — a deliberate
  contract choice (see `RoomSearchRequest`/`CreateBookingRequest`
  validators), not an oversight.
- RBAC is a simplification: any `User.role != "guest"` is treated as staff
  (`_is_staff` in `booking_service.py`) since this repo doesn't have a
  defined role enum yet.
