from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.core.database import get_db
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    System health check.
    Returns status of app, database, and Redis.
    This endpoint is PUBLIC — no authentication required.
    """
    import redis.asyncio as aioredis  # lazy import — avoids forcing redis dep at import time

    health = {
        "status": "ok",
        "environment": settings.environment,
        "services": {},
    }

    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health["services"]["database"] = "connected"
    except Exception as e:
        health["services"]["database"] = f"error: {str(e)}"
        health["status"] = "degraded"

    # Check Redis
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        health["services"]["redis"] = "connected"
    except Exception as e:
        health["services"]["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"

    return health
