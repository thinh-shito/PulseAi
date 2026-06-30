from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    workflow_id: Optional[str] = None
    session_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    reply: str
    workflow_id: Optional[str] = None
    session_id: Optional[str] = None