from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


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

    # AI Agent Service URL
    ai_agent_url: str = "http://localhost:4000"

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
