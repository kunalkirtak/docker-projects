"""Configuration for the agent service."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "docker-agent-platform-agent"
    log_level: str = "INFO"

    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "agent_knowledge"

    worker_service_host: str = "worker"
    worker_service_port: int = 8002

    request_timeout_seconds: float = 10.0
    request_max_retries: int = 3

    embedding_dimensions: int = 128

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def worker_service_url(self) -> str:
        return f"http://{self.worker_service_host}:{self.worker_service_port}"


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
