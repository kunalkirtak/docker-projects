"""
Application configuration.

All configuration is loaded from environment variables so that no
secrets or environment-specific values are hard-coded into the
application. Docker Compose injects these values at container start
time (see docker-compose.yml and .env.example).
"""

import os
from dataclasses import dataclass


def _get_env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # PostgreSQL
    postgres_host: str = _get_env("POSTGRES_HOST", "postgres")
    postgres_port: str = _get_env("POSTGRES_PORT", "5432")
    postgres_db: str = _get_env("POSTGRES_DB", "ragdb")
    postgres_user: str = _get_env("POSTGRES_USER", "raguser")
    postgres_password: str = _get_env("POSTGRES_PASSWORD", "ragpassword")

    # Qdrant
    qdrant_host: str = _get_env("QDRANT_HOST", "qdrant")
    qdrant_port: str = _get_env("QDRANT_PORT", "6333")
    qdrant_collection: str = _get_env("QDRANT_COLLECTION", "documents")

    # Embeddings
    embedding_dim: int = int(_get_env("EMBEDDING_DIM", "128"))

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"


settings = Settings()
