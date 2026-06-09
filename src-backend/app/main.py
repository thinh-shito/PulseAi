from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown logic."""
    import os
    import logging

    # ── Configure LangSmith tracing (production monitoring) ──────────────
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        print(f"🔍 LangSmith tracing ENABLED — project: {settings.langchain_project}")
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

    # ── Production: block PHI from file logs (HIPAA rule) ────────────────
    if settings.is_production:
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                logging.root.removeHandler(handler)
                print("🔒 PHI file logging removed (production mode)")

    print(f"🚀 PulseAI Backend starting in '{settings.environment}' mode")
    yield
    # Shutdown
    print("🛑 PulseAI Backend shutting down")



def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    app = FastAPI(
        title="PulseAI Backend API",
        description="Medical AI platform for automated Prior Authorization workflows",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API router
    app.include_router(api_router, prefix="/api/v1")

    # Public health endpoint (no /api/v1 prefix for Docker healthcheck)
    from app.api.v1.endpoints.health import router as health_router
    app.include_router(health_router)

    return app


app = create_app()
