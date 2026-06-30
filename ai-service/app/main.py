from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router
from app.core.config import settings
from app.integrations.redis import cleanup_redis_cache, init_redis_cache


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize optional integrations on startup and clean them up on shutdown."""
    await init_redis_cache(settings.redis_url)

    yield

    await cleanup_redis_cache()


app = FastAPI(
    title="PulseAI — AI Service",
    description="LangGraph prior authorization AI pipeline",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def root_health():
    return {"status": "ok", "service": "ai-service"}