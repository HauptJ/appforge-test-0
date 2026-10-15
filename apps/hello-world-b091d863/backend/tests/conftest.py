"""Shared test fixtures."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

# Set env BEFORE importing the app factory
os.environ.setdefault("AUTH_DEV_BYPASS", "true")
os.environ.setdefault("ALLOW_ENV_CREDENTIALS", "true")
# Use obviously fake test values, built at runtime.
os.environ.setdefault("SESSION_SIGNING_KEY", "test-" + uuid.uuid4().hex)
os.environ.setdefault("OIDC_CLIENT_SECRET", "test-" + uuid.uuid4().hex)
os.environ.setdefault("ALLOWED_ORIGINS", "http://testserver")
os.environ.setdefault("DOCS_ENABLED", "false")

from app.config import Settings, get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    return TestClient(app, base_url="http://testserver")


@pytest.fixture
def logged_in_client(client: TestClient) -> TestClient:
    # Trigger dev-bypass login; follow redirects so cookies land.
    r = client.get("/api/v1/auth/login", follow_redirects=False)
    assert r.status_code == 302, r.text
    return client
