"""Tests for the hello endpoint and health probes."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_hello_returns_hello_world(client: TestClient) -> None:
    response = client.get("/api/v1/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_hello_sets_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/hello")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Frame-Options"] == "DENY"


def test_hello_returns_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/hello")
    rid = response.headers.get("X-Request-ID", "")
    assert rid and len(rid) <= 64


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_docs_disabled_by_default(client: TestClient) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_oversized_body_rejected(client: TestClient) -> None:
    # Declare a Content-Length larger than the 1 MiB cap.
    response = client.post(
        "/api/v1/hello",
        headers={"content-length": str(2 * 1024 * 1024)},
        content=b"x",
    )
    assert response.status_code in (405, 413)  # 405 if method rejected first
