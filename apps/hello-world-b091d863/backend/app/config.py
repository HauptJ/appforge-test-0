"""Application configuration. Non-secret settings only; credentials come from Vault."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Hello World"
    environment: str = Field(default="development")
    docs_enabled: bool = Field(default=False)

    # OIDC (non-secret settings)
    oidc_issuer: str = Field(default="")
    oidc_client_id: str = Field(default="")
    oidc_redirect_url: str = Field(default="http://localhost:8080/api/v1/auth/callback")
    oidc_scopes: str = Field(default="openid profile email")

    # Session
    session_cookie_name: str = Field(default="hw_session")
    session_idle_minutes: int = Field(default=30)
    session_absolute_minutes: int = Field(default=480)

    # Hardening
    allowed_origins: str = Field(default="http://localhost:8080")
    serve_over_tls: bool = Field(default=False)

    # Auth bypass for local dev / tests only - never set true in production
    auth_dev_bypass: bool = Field(default=False)
    dev_user_email: str = Field(default="dev@example.com")
    dev_user_name: str = Field(default="Dev User")

    @property
    def allowed_origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
