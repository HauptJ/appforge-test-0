def test_status_unauthenticated(client):
    r = client.get("/api/v1/auth/status")
    assert r.status_code == 200
    assert r.json() == {"authenticated": False, "user": None}


def test_dev_login_sets_cookies(client):
    r = client.get("/api/v1/auth/login", follow_redirects=False)
    assert r.status_code == 302
    cookies = {k.lower(): v for k, v in r.cookies.items()}
    assert "hw_session" in cookies
    assert "csrf_token" in cookies


def test_status_authenticated(logged_in_client):
    r = logged_in_client.get("/api/v1/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is True
    assert body["user"]["email"] == "dev@example.com"


def test_logout_requires_csrf(logged_in_client):
    # Missing CSRF header -> 403
    r = logged_in_client.post("/api/v1/auth/logout", follow_redirects=False)
    assert r.status_code == 403


def test_logout_with_csrf(logged_in_client):
    csrf = logged_in_client.cookies.get("csrf_token")
    assert csrf
    r = logged_in_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf, "Origin": "http://testserver"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    # Session cookie cleared
    r2 = logged_in_client.get("/api/v1/auth/status")
    assert r2.json()["authenticated"] is False
