from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agents.concierge.agent import concierge_agent
from agents.reservation.agent_context import ReservationContext
from app.db.database import get_db
from app.models.user import User
from app.security.jwt import get_current_user


router = APIRouter(prefix="/concierge", tags=["concierge"])


class ConciergeChatRequest(BaseModel):
    message: str = Field(min_length=1)
    operation: str | None = None
    payload: dict = Field(default_factory=dict)


@router.post("/chat")
async def concierge_chat(
    request: ConciergeChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await concierge_agent.handle_message(
        ReservationContext(db=db, current_user=current_user),
        {
            "message": request.message,
            "operation": request.operation,
            "payload": request.payload,
        },
    )
