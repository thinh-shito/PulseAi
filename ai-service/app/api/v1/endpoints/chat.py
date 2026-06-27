"""
Chat endpoint calling the chat handler.
"""
from fastapi import APIRouter
from app.handlers.chat_handler import handle_chat
from app.models.chat_models import ChatRequest

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Send message to the chat handler.
    """
    res = handle_chat(request.message)
    return {
        "reply": res["reply"],
        "workflow_id": request.workflow_id,
    }