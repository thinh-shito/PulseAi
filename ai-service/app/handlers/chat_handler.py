"""
Chat Handler.
"""
from typing import Any, Dict, Optional

import asyncio

from app.services_ai.chat_agent import run_chat_agent, stream_chat_agent


def handle_chat(
    message: str,
    session_id: Optional[str] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    """
    Handle the chat inquiry using the LangGraph agent.
    """
    if stream:
        # Streaming must be handled by the FastAPI endpoint (async generator).
        raise NotImplementedError("Streaming is only supported in the API endpoint.")
    return asyncio.run(run_chat_agent(message, session_id=session_id))
