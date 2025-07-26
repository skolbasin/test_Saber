"""Application configuration management."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden via environment variables.
    Example: DATABASE_URL, REDIS_DSN, API_V1_PREFIX
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./saber.db",
        description="Database connection URL"
    )
    
    redis_dsn: str = Field(
        default="redis://localhost:6379",
        description="Redis connection DSN"
    )
    
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="API v1 URL prefix"
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    cors_origins: List[str] = Field(
        default=["http://localhost:8000", "http://localhost:3000"],
        description="CORS allowed origins"
    )
    
    cache_ttl: int = Field(
        default=3600,
        description="Default cache TTL in seconds"
    )
    
    max_workers: int = Field(
        default=4,
        description="Maximum number of worker processes"
    )
    
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    
    tasks_config_path: str = Field(
        default="builds/tasks.yaml",
        description="Path to tasks configuration file"
    )
    
    builds_config_path: str = Field(
        default="builds/builds.yaml",
        description="Path to builds configuration file"
    )
    
    topological_sort_algorithm: str = Field(
        default="kahn",
        description="Default topological sort algorithm (kahn or dfs)"
    )
    
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        description="JWT secret key for token signing"
    )
    
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT algorithm for token signing"
    )
    
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return not self.debug

    @property
    def database_is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")

    @property
    def database_is_postgres(self) -> bool:
        """Check if using PostgreSQL database."""
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings instance.
    
    Returns:
        Singleton settings instance
    """
    return Settings()