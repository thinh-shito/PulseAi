from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    workflow_id: Optional[str] = None