"""Runs API endpoints for AI agent orchestration."""
import uuid
import json
from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from api.schemas.runs import (
    CreateRunRequest,
    ContinueRunRequest,
    RunResponse,
    RunStatusResponse,
)
from core.database import DatabasePool
from agent.loop import run_agent_loop


router = APIRouter(prefix="/v1/runs", tags=["runs"])


async def get_or_create_session(session_id: str | None) -> str:
    """Get existing session or create a new one."""
    pool = await DatabasePool.get_pool()
    
    if session_id:
        # Verify session exists
        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM sessions_v2 WHERE id = $1)",
                session_id
            )
            if exists:
                return session_id
    
    # Create new session
    new_session_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO sessions_v2 (id, created_at) VALUES ($1, $2)",
            new_session_id,
            int(datetime.now().timestamp() * 1000)
        )
    
    return new_session_id


async def create_conversation(session_id: str) -> str:
    """Create a new conversation within a session."""
    pool = await DatabasePool.get_pool()
    conversation_id = str(uuid.uuid4())
    
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversations_v2 
            (id, session_id, title, created_at, last_message_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            conversation_id,
            session_id,
            "New Conversation",
            int(datetime.now().timestamp() * 1000),
            int(datetime.now().timestamp() * 1000)
        )
    
    return conversation_id


@router.post("", response_model=RunResponse)
async def create_run(request: CreateRunRequest, response: Response):
    """
    Create a new run and start the agent loop.
    Returns immediately with run metadata; client should connect to SSE for streaming.
    """
    # Get or create session
    session_id = await get_or_create_session(request.session_id)
    
    # Create conversation
    conversation_id = await create_conversation(session_id)
    
    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=2592000  # 30 days
    )
    
    # Run ID is the same as conversation ID for simplicity
    run_id = conversation_id
    
    # Save user message to database
    pool = await DatabasePool.get_pool()
    message_content = request.message
    if request.file_content and request.file_name:
        message_content = f"{message_content}\n--- ATTACHED FILE: {request.file_name} ---\n{request.file_content}"
        
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO messages_v2 (conversation_id, role, content, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            run_id,
            "user",
            message_content,
            int(datetime.now().timestamp() * 1000)
        )
    
    return RunResponse(
        run_id=uuid.UUID(run_id),
        session_id=uuid.UUID(session_id),
        conversation_id=uuid.UUID(conversation_id),
        status="running",
        created_at=datetime.now(),
    )


@router.post("/{run_id}/continue", response_model=RunResponse)
async def continue_run(run_id: str, request: ContinueRunRequest):
    """Continue a paused run with additional user input."""
    # Verify conversation exists
    pool = await DatabasePool.get_pool()
    
    async with pool.acquire() as conn:
        conv = await conn.fetchrow(
            "SELECT id, session_id FROM conversations_v2 WHERE id = $1",
            run_id
        )
        
        if not conv:
            raise HTTPException(status_code=404, detail="Run not found")
            
        # Save follow-up user message to database
        await conn.execute(
            """
            INSERT INTO messages_v2 (conversation_id, role, content, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            run_id,
            "user",
            request.message,
            int(datetime.now().timestamp() * 1000)
        )
    
    return RunResponse(
        run_id=uuid.UUID(run_id),
        session_id=uuid.UUID(conv["session_id"]),
        conversation_id=uuid.UUID(run_id),
        status="running",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str):
    """Get the current status of a run."""
    pool = await DatabasePool.get_pool()
    
    async with pool.acquire() as conn:
        conv = await conn.fetchrow(
            """
            SELECT id, session_id, title, created_at, last_message_at
            FROM conversations_v2 
            WHERE id = $1
            """,
            run_id
        )
        
        if not conv:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get last message to determine status
        last_message = await conn.fetchrow(
            """
            SELECT role, content 
            FROM messages_v2 
            WHERE conversation_id = $1 
            ORDER BY id DESC 
            LIMIT 1
            """,
            run_id
        )
        
        # Check for exported files
        files = await conn.fetch(
            """
            SELECT id, file_name, mime_type
            FROM exported_files_v2
            WHERE conversation_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            run_id
        )
    
    status = "completed" if last_message and last_message["role"] == "assistant" else "running"
    
    result = None
    if last_message and last_message["role"] == "assistant":
        result = {
            "response": last_message["content"],
            "file_ready": {
                "file_id": files[0]["id"],
                "file_name": files[0]["file_name"],
                "mime_type": files[0]["mime_type"]
            } if files else None
        }
    
    return RunStatusResponse(
        run_id=uuid.UUID(run_id),
        session_id=uuid.UUID(conv["session_id"]),
        conversation_id=uuid.UUID(run_id),
        status=status,
        result=result,
        error=None,
        created_at=datetime.fromtimestamp(conv["created_at"] / 1000),
        updated_at=datetime.fromtimestamp(conv["last_message_at"] / 1000),
    )


@router.get("/{run_id}/events")
async def stream_run_events(run_id: str):
    """
    Stream Server-Sent Events for a run.
    This should be called immediately after creating a run to receive live updates.
    """
    pool = await DatabasePool.get_pool()
    
    # Verify conversation exists and get details
    async with pool.acquire() as conn:
        conv = await conn.fetchrow(
            "SELECT id, session_id FROM conversations_v2 WHERE id = $1",
            run_id
        )
        
        if not conv:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get the last user message to process
        last_user_message = await conn.fetchrow(
            """
            SELECT content 
            FROM messages_v2 
            WHERE conversation_id = $1 AND role = 'user'
            ORDER BY id DESC 
            LIMIT 1
            """,
            run_id
        )
        
        if not last_user_message:
            raise HTTPException(status_code=400, detail="No user message found for this run")
    
    user_message = last_user_message["content"]
    
    # Parse file attachment if present
    file_content = None
    file_name = None
    if "--- ATTACHED FILE:" in user_message:
        try:
            parts = user_message.split("--- ATTACHED FILE: ")
            if len(parts) > 1:
                subparts = parts[1].split(" ---\n", 1)
                if len(subparts) == 2:
                    file_name = subparts[0].strip()
                    file_content = subparts[1].strip()
                    # Strip the attachment text from the user message for LLM
                    user_message = parts[0].strip()
        except Exception:
            pass
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from the agent loop."""
        async for event in run_agent_loop(run_id, user_message, file_content, file_name):
            event_type = event["event"]
            data = event["data"]
            yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    return EventSourceResponse(event_generator())


@router.get("/files/{file_id}")
async def download_file(file_id: str):
    """Download an exported file by ID."""
    from services.file_export import get_exported_file
    import base64
    
    file_data = await get_exported_file(file_id)
    
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Decode base64 content
    content = base64.b64decode(file_data["content_base64"])
    
    return Response(
        content=content,
        media_type=file_data["mime_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"'
        }
    )