from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


@dataclass
class FeedbackContext:
    """Everything the Feedback Agent's tools need to do real work.

    Built once per request at the API layer — a db session plus the
    authenticated user from get_current_user — and passed down through
    handle_message/handle_task, mirroring ReservationContext. current_user
    is the only source of truth for "who is submitting this review";
    tools never trust a user id carried inside a message payload.
    """

    db: Session
    current_user: Optional[User] = None
