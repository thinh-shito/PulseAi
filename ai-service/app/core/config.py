from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    environment: str = "development"

    # LLM API Keys
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "pulseai-development"

    # Internal security — shared secret between backend and ai-service
    internal_api_key: str = "internal-secret-change-in-production"

    # Backend callback URL for workflow progress updates
    backend_callback_url: str = "http://backend:4000"

    # Database connection URL
    database_url: str = "postgresql://pulseai:pulseai_secret@postgres:5432/pulseai_db"

    # External HIS database connection URL used by /chat medical document search.
    # This database is separate from PulseAI's application database.
    his_database_url: Optional[str] = None
    his_db_query_fast_model: str = "gpt-4o-mini"

    # Redis connection URL — optional; app runs without LLM cache when unset
    redis_url: Optional[str] = None

    # CORS — which origins can call ai-service directly (dev only)
    allowed_origins: str = "http://localhost:4000,http://backend:4000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()