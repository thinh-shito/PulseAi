"""Pydantic schemas for Runs API requests and responses."""
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class CreateRunRequest(BaseModel):
    """Request schema for creating a new run."""
    message: str = Field(..., description="User message or clinical note content")
    file_content: Optional[str] = Field(None, description="Base64 encoded file content")
    file_name: Optional[str] = Field(None, description="Name of the uploaded file")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


class ContinueRunRequest(BaseModel):
    """Request schema for continuing a paused run."""
    message: str = Field(..., description="Follow-up message or clinical correction")


class FileReadyInfo(BaseModel):
    """Information about a generated file ready for download."""
    file_id: str
    file_name: str
    mime_type: str


class RunResult(BaseModel):
    """Result data for a completed run."""
    response: str
    file_ready: Optional[FileReadyInfo] = None


RunStatus = Literal["running", "completed", "failed", "waiting_for_input"]


class RunResponse(BaseModel):
    """Response schema for run creation."""
    run_id: UUID
    session_id: UUID
    conversation_id: UUID
    status: RunStatus
    created_at: datetime
    updated_at: Optional[datetime] = None


class RunStatusResponse(BaseModel):
    """Response schema for run status queries."""
    run_id: UUID
    session_id: UUID
    conversation_id: UUID
    status: RunStatus
    result: Optional[RunResult] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime