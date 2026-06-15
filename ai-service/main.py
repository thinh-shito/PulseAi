"""Main entrypoint for PulseAI AI Service - FastAPI application."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.database import init_db, DatabasePool
from services.mcp_client import close_mcp_client
from api.v1.endpoints import runs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle handler for startup and shutdown events."""
    # Startup
    print("[ai-service] Initializing database connection...")
    await init_db()
    print(f"[ai-service] AI Service starting on port {settings.port}")
    print(f"[ai-service] MCP Server URL: {settings.mcp_server_url}")
    
    yield
    
    # Shutdown
    print("[ai-service] Shutting down...")
    await close_mcp_client()
    await DatabasePool.close_pool()


app = FastAPI(
    title="PulseAI AI Service",
    description="AI Orchestration and Runs API for medical documentation automation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin] if settings.cors_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(runs.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "ai-service",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )