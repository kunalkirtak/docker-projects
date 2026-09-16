"""Application configuration.

All configuration is read from environment variables so that the same
container image can be promoted through different environments without
code changes. Never hard-code service addresses or secrets here.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "docker-agent-platform-api"
    environment: str = "development"
    log_level: str = "INFO"

    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "agentdb"
    postgres_user: str = "agentuser"
    postgres_password: str = "agentpassword"

    # Downstream services (Docker Compose service names, NOT localhost)
    agent_service_host: str = "agent"
    agent_service_port: int = 8001

    worker_service_host: str = "worker"
    worker_service_port: int = 8002

    # HTTP client behaviour
    request_timeout_seconds: float = 10.0
    request_max_retries: int = 3

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def agent_service_url(self) -> str:
        return f"http://{self.agent_service_host}:{self.agent_service_port}"

    @property
    def worker_service_url(self) -> str:
        return f"http://{self.worker_service_host}:{self.worker_service_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
