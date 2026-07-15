from app import create_app


def test_auth_login_returns_token() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "securepassword"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Authentication successful"
    assert data["user"]["email"] == "user@example.com"
    assert "token" in data


def test_auth_me_requires_token() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.get("/auth/me")

    assert response.status_code == 401


def test_auth_logout_requires_token() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post("/auth/logout")

    assert response.status_code == 401


def test_auth_me_with_valid_token() -> None:
    app = create_app("testing")
    client = app.test_client()

    login_resp = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "securepassword"},
    )
    token = login_resp.get_json()["token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.get_json()["message"] == "User session valid"


def test_auth_login_requires_valid_email() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/auth/login",
        json={"email": "invalid", "password": "securepassword"},
    )

    assert response.status_code == 400
