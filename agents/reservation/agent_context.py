from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


@dataclass
class ReservationContext:
    """Everything the Reservation Agent's tools need to do real work.

    Built once per request at the API layer — a db session plus the
    authenticated user from `get_current_user` — and passed down through
    handle_message/handle_task. Tools never construct their own db session,
    and the agent never trusts a user id carried inside a message payload;
    `current_user` on this context is the only source of truth for "who is
    making this request."
    """

    db: Session
    current_user: Optional[User] = None