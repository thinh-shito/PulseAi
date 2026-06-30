"""
Chat endpoint calling the chat handler.
"""
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from app.handlers.chat_handler import handle_chat
from app.models.chat_models import ChatRequest, ChatResponse
from app.services_ai.chat_agent import stream_chat_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request):
    """
    Send message to the chat handler. Supports streaming and session.
    """
    data = await request.json()
    chat_req = ChatRequest(**data)

    if chat_req.stream:
        async def event_stream():
            async for chunk in stream_chat_agent(
                chat_req.message,
                session_id=chat_req.session_id,
            ):
                yield chunk
        return StreamingResponse(event_stream(), media_type="text/plain")

    res = handle_chat(
        chat_req.message,
        session_id=chat_req.session_id,
        stream=False,
    )
    return ChatResponse(
        reply=res["reply"],
        workflow_id=chat_req.workflow_id,
        session_id=chat_req.session_id,
    )
