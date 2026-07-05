from app import create_app


def test_auth_login_returns_pending_cognito_message() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "securepassword"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Authentication service is ready. Amazon Cognito integration will be implemented in Sprint 3."
    }


def test_auth_me_returns_pending_cognito_message() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Authentication service is ready. Amazon Cognito integration will be implemented in Sprint 3."
    }


def test_auth_logout_returns_pending_cognito_message() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post("/auth/logout")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Authentication service is ready. Amazon Cognito integration will be implemented in Sprint 3."
    }
