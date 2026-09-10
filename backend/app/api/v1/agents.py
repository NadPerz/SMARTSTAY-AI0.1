from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from agents.concierge.agent import concierge_agent
from app.models.user import User
from app.security.jwt import get_current_user


router = APIRouter(prefix="/concierge", tags=["concierge"])


class ConciergeChatRequest(BaseModel):
    message: str = Field(min_length=1)


@router.post("/chat")
async def concierge_chat(
    request: ConciergeChatRequest,
    current_user: User = Depends(get_current_user),
):
    return await concierge_agent.handle_message(None, request.message)
