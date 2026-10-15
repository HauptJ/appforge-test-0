def test_body_too_large(client):
    big = "x" * (200 * 1024)
    r = client.post(
        "/api/v1/auth/logout",
        content=big,
        headers={"Content-Type": "application/json", "Content-Length": str(len(big))},
    )
    assert r.status_code == 413
