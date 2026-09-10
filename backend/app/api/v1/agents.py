from fastapi import APIRouter
from pydantic import BaseModel, Field

from agents.concierge.agent import concierge_agent


router = APIRouter(prefix="/concierge", tags=["concierge"])


class ConciergeChatRequest(BaseModel):
    message: str = Field(min_length=1)


@router.post("/chat")
async def concierge_chat(request: ConciergeChatRequest):
    return await concierge_agent.handle_message(None, request.message)
