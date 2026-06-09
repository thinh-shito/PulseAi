"""
Presence API — Real-time user online/offline status endpoints.

Endpoints:
  POST /presence/heartbeat      — mark current user online (call every 30s)
  DELETE /presence/offline      — mark current user offline (on logout)
  GET  /presence/me             — get my own online status
  GET  /presence/users          — bulk query for a list of user UUIDs (admin/doctor)
  GET  /presence/stats          — total online count + system stats
  GET  /presence/stream         — SSE stream: real-time online count updates
"""

import asyncio
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.domain.models.user import User
from app.services.presence_service import PresenceService, get_presence_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/presence", tags=["presence"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class HeartbeatResponse(BaseModel):
    online: bool
    user_id: str
    message: str


class PresenceStatusResponse(BaseModel):
    user_id: str
    online: bool
    last_seen: Optional[str]


class BulkPresenceRequest(BaseModel):
    user_ids: List[str]


class PresenceStatsResponse(BaseModel):
    online_users: int
    total_registered: int
    bitmap_key: str
    ttl_seconds: int


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    current_user: User = Depends(get_current_user),
    presence: PresenceService = Depends(get_presence_service),
):
    """
    Mark the current user as ONLINE.

    Frontend should call this:
    - Immediately after login
    - Every 30 seconds to maintain online status
    - On tab focus / visibility change

    Uses Redis SETBIT — O(1) operation.
    """
    user_id = str(current_user.id)
    await presence.heartbeat(user_id, display_name=current_user.full_name)
    return HeartbeatResponse(
        online=True,
        user_id=user_id,
        message="Presence updated",
    )


@router.delete("/offline", status_code=204)
async def mark_offline(
    current_user: User = Depends(get_current_user),
    presence: PresenceService = Depends(get_presence_service),
):
    """
    Mark the current user as OFFLINE immediately.

    Call on logout or browser close (beforeunload).
    Uses Redis SETBIT offset 0 — O(1).
    """
    await presence.mark_offline(str(current_user.id))


@router.get("/me", response_model=PresenceStatusResponse)
async def get_my_status(
    current_user: User = Depends(get_current_user),
    presence: PresenceService = Depends(get_presence_service),
):
    """
    Get current user's own online status and last heartbeat time.
    Uses Redis GETBIT — O(1).
    """
    user_id = str(current_user.id)
    online = await presence.is_online(user_id)
    last_seen = await presence.get_last_seen(user_id)
    return PresenceStatusResponse(
        user_id=user_id,
        online=online,
        last_seen=last_seen,
    )


@router.post("/users", response_model=dict)
async def get_bulk_presence(
    body: BulkPresenceRequest,
    current_user: User = Depends(get_current_user),
    presence: PresenceService = Depends(get_presence_service),
):
    """
    Bulk query online status for a list of user UUIDs.

    Uses Redis pipeline for a single round-trip regardless of list size.
    Returns: {"<uuid>": true/false, ...}

    Only DOCTOR and ADMIN roles can query other users' presence.
    """
    from app.core.security import Role
    if current_user.role == Role.VIEWER and any(
        uid != str(current_user.id) for uid in body.user_ids
    ):
        raise HTTPException(
            status_code=403,
            detail="Viewers can only query their own presence",
        )

    presence_map = await presence.get_presence_bulk(body.user_ids)
    return presence_map


@router.get("/stats", response_model=PresenceStatsResponse)
async def get_presence_stats(
    current_user: User = Depends(get_current_user),
    presence: PresenceService = Depends(get_presence_service),
):
    """
    Get total online user count using Redis BITCOUNT — O(n/8).

    BITCOUNT scans the bitmap and counts all set bits (1s).
    For 1 million users, the bitmap is only 125 KB.
    """
    stats = await presence.get_stats()
    return PresenceStatsResponse(**stats)


@router.get("/stream")
async def stream_presence(
    current_user: User = Depends(get_current_user),
    presence: PresenceService = Depends(get_presence_service),
    interval: int = Query(default=10, ge=5, le=60, description="Poll interval seconds"),
):
    """
    Server-Sent Events stream — pushes real-time online count every N seconds.

    Client receives: data: {"online_users": 42, "timestamp": "..."}

    Uses BITCOUNT on every tick — extremely efficient even at massive scale.
    """
    async def event_generator():
        try:
            while True:
                stats = await presence.get_stats()
                from datetime import datetime, timezone
                payload = json.dumps({
                    "online_users": stats["online_users"],
                    "total_registered": stats["total_registered"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                yield f"data: {payload}\n\n"
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.debug("Presence SSE stream closed by client")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
