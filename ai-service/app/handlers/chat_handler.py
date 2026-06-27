"""
Chat Handler.
"""
from typing import Dict, Any
from app.core.chain import chat_chain
from app.prompts.chat_prompt import CHAT_PROMPT


def handle_chat(message: str) -> Dict[str, Any]:
    """
    Handle the chat inquiry using the LLM chain.
    """
    prompt = CHAT_PROMPT.format(message=message)
    response = chat_chain.invoke(prompt)

    try:
        reply = response.content.strip()
    except AttributeError:
        reply = str(response).strip()

    return {"reply": reply}