"""Application settings and configuration."""

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application settings
    debug: bool = Field(False)
    environment: str = Field("development")
    host: str = Field("0.0.0.0")
    port: int = Field(8000)

    # Raw database components
    postgres_user: str = Field(..., alias="POSTGRES_USER")
    postgres_password: str = Field(..., alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(..., alias="POSTGRES_DB")
    postgres_host: str = Field("localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")

    # Computed database URL
    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis settings
    redis_url: str = Field("redis://localhost:6379")

    # JWT settings
    jwt_secret_key: str = Field("your-secret-key-change-in-production")
    jwt_algorithm: str = Field("HS256")
    jwt_access_token_expire_minutes: int = Field(30)
    jwt_refresh_token_expire_days: int = Field(7)

    # API settings
    api_title: str = Field("Saber Build System API")
    api_version: str = Field("1.0.0")
    api_description: str = Field("Enterprise build system with topological task sorting")

    # CORS settings
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])

    # Celery settings
    celery_broker_url: str = Field("redis://localhost:6379/0")
    celery_result_backend: str = Field("redis://localhost:6379/0")

    # Logging settings
    log_level: str = Field("INFO")
    log_format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Security settings
    bcrypt_rounds: int = Field(12)

    # Performance settings
    max_connections: int = Field(20)
    connection_timeout: int = Field(30)

    # File paths
    config_dir: str = Field("./config")
    tasks_config_file: str = Field("tasks.yaml")
    builds_config_file: str = Field("builds.yaml")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "forbid",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
