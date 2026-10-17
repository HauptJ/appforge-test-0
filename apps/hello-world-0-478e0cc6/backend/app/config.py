"""Application configuration loaded from environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    All values come from the environment. This app needs no credentials, so
    there is nothing to fetch from Vault.
    """

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    docs_enabled: bool = False
    max_body_bytes: int = 1_048_576  # 1 MiB
    app_name: str = "hello-world-0"
    app_version: str = "0.1.0"


def get_settings() -> Settings:
    """Return a fresh Settings instance (cheap; called once at startup)."""
    return Settings()
