import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.database import get_db
from app.domain.models.user import User
from app.domain.models.workflow import Workflow
from app.domain.models.audit_log import AuditLog
from app.domain.phi_filter import anonymize_phi
from app.infra.ai_client import ai_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class HistoryItem(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("Role must be 'user' or 'assistant'")
        return v


class ChatRequest(BaseModel):
    message: str
    workflow_id: Optional[str] = None
    history: List[HistoryItem] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    action: Optional[str] = None
    anonymized: str


@router.post("", response_model=ChatResponse)
async def chat_assistant(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = request.message
    history = request.history
    workflow_id = request.workflow_id

    # 1. Request body validation
    if not message or message.strip() == "":
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if len(message) > 10000:
        raise HTTPException(
            status_code=400, detail="Message exceeds maximum character length (10000)")
    if len(message.split()) > 1000:
        raise HTTPException(
            status_code=400, detail="Message exceeds maximum word limit (1000)")

    # 2. Run anonymize_phi on the message
    anonymized_msg = anonymize_phi(message)

    # 3. Retrieve workflow details if workflow_id is provided
    workflow = None
    if workflow_id:
        try:
            wf_uuid = uuid.UUID(str(workflow_id))
            stmt = select(Workflow).where(Workflow.id == wf_uuid)
            result = await db.execute(stmt)
            workflow = result.scalar_one_or_none()
        except (ValueError, AttributeError):
            workflow = None

        if not workflow:
            # Invalid/non-existing workflow ID: return status 200 with "No matching workflow" reply
            return ChatResponse(
                reply="No matching workflow found.",
                action=None,
                anonymized=anonymized_msg,
            )

    # 4. Log a CHAT_QUERY action in the audit_logs table
    audit_log = AuditLog(
        user_id=current_user.id,
        action="CHAT_QUERY",
        patient_id=workflow.patient_id if workflow else None,
        workflow_id=workflow.id if workflow else None,
        resource_type="workflow" if workflow else "chat",
        resource_id=str(workflow.id) if workflow else "global",
    )
    db.add(audit_log)
    await db.commit()

    # 5. Detect clinical triggers (case-insensitive checks)
    message_lower = message.lower()
    triggers = [
        "spinal injection",
        "start a new case",
        "create workflow",
        "new workflow",
        "prior authorization for jane",
    ]
    action = None
    if any(trigger in message_lower for trigger in triggers):
        action = "offer_create_workflow"

    # 6. Call AI Agent API
    session_id = str(workflow_id) if workflow_id else "global"
    reply = await ai_client.call_chat(session_id=session_id, message=anonymized_msg)

    # For clinical triggers or fallback if ai response is empty/error, we can customize
    if action == "offer_create_workflow" and not reply.startswith("Error"):
        reply = f"I detected a clinical need for a workflow. Would you like to create a new workflow? Trigger message: {message}"

    return ChatResponse(reply=reply, action=action, anonymized=anonymized_msg)