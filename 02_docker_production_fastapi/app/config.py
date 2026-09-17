"""Application configuration.

All configuration is sourced from environment variables (optionally via a
.env file for local development). Nothing here is hard-coded for a specific
environment: the same image is promoted from dev -> staging -> production by
changing environment variables only.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the application."""

    app_name: str = "Production FastAPI Container"
    environment: str = "development"
    log_level: str = "INFO"
    data_file: str = "/app/data/items.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the environment is only parsed once per process, while still
    being overridable in tests via ``get_settings.cache_clear()``.
    """
    return Settings()
