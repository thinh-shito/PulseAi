"""
Chat endpoint stub — placeholder for future streaming LLM chat.
Currently returns a not-implemented response.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    workflow_id: str | None = None


@router.post("/chat")
async def chat(request: ChatRequest):
    # TODO: implement streaming LLM chat using LangChain
    return {
        "reply": "Chat endpoint not yet implemented in ai-service.",
        "workflow_id": request.workflow_id,
    }