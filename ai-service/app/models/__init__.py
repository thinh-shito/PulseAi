"""
Pydantic Request and Response Models.
"""
from app.models.chat_models import ChatRequest
from app.models.document_model import get_document_output_model

__all__ = [
    "ChatRequest",
    "get_document_output_model",
]