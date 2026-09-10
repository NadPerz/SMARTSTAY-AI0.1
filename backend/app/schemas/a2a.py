from pydantic import BaseModel
from typing import Dict, Any, Optional

class A2ARequest(BaseModel):
    user_id: str
    intent: str
    payload: Dict[str, Any]

class A2AResponse(BaseModel):
    status: str
    agent: str
    data: Dict[str, Any]
    error: Optional[str] = None