from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    environment: str = "development"
    secret_key: str = "changeme-min-32-chars-replace-in-prod"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = "postgresql+asyncpg://pulseai:pulseai_secret@localhost:5432/pulseai_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Azure OpenAI (primary)
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_api_version: str = "2024-02-01"
    azure_openai_deployment: str = "gpt-4o"

    # Fallback LLMs (dev only)
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "pulseai-development"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"


settings = Settings()
