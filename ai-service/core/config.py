"""Configuration settings for AI service using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Server settings
    port: int = 4000
    host: str = "0.0.0.0"
    cors_origin: str = "*"
    
    # OpenAI settings
    openai_api_key: str
    openai_model: str = "gpt-4o"
    
    # Database settings
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "pulseai"
    postgres_password: str = "pulseai_secret"
    postgres_db: str = "pulseai_db"
    
    # MCP Server settings
    mcp_server_url: str = "http://localhost:5000"
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection string."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()