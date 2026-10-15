from app.services.hello_service import build_hello_message


def test_hello_requires_auth(client):
    r = client.get("/api/v1/hello")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_hello_authenticated(logged_in_client):
    r = logged_in_client.get("/api/v1/hello")
    assert r.status_code == 200
    body = r.json()
    assert "Hello, world" in body["message"]
    assert "Dev User" in body["message"]


def test_hello_rejects_unknown_fields(logged_in_client):
    # The GET endpoint ignores query, but response model forbids extras: check schema.
    from app.models.schemas import HelloResponse
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        HelloResponse(message="x", extra="y")  # type: ignore[call-arg]


def test_build_hello_message_defaults():
    assert "world" in build_hello_message("")
    assert "Alice" in build_hello_message("Alice")


def test_hello_bad_origin(logged_in_client):
    csrf = logged_in_client.cookies.get("csrf_token")
    # Only state-changing methods check origin; GET is safe. POST on hello doesn't exist, so hit logout.
    r = logged_in_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf or "", "Origin": "http://evil.example.com"},
        follow_redirects=False,
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden_origin"
