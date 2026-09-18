from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


@dataclass
class RecommendationContext:
    db: Session
    current_user: Optional[User] = None