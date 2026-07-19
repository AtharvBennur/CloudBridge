from app import create_app
from app.middleware.auth import encode_token


def _auth_headers():
    token = encode_token("test-user", "test@example.com", "Test User")
    return {"Authorization": f"Bearer {token}"}


def test_create_aws_connection_returns_created_record() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["aws_account_id"] == "123456789012"
    assert data["connection_status"] == "PENDING"
    assert data["external_id"]
    assert data["role_arn"] == ""  # No role ARN provided


def test_create_aws_connection_with_role_arn() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
            "role_arn": "arn:aws:iam::123456789012:role/CloudBridgeRole",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["role_arn"] == "arn:aws:iam::123456789012:role/CloudBridgeRole"


def test_list_aws_connections_returns_collection() -> None:
    app = create_app("testing")
    client = app.test_client()

    client.post(
        "/aws-connections",
        json={
            "aws_account_id": "111111111111",
            "aws_region": "eu-west-1",
        },
        headers=_auth_headers(),
    )

    response = client.get("/aws-connections", headers=_auth_headers())

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert response.get_json()[0]["aws_account_id"] == "111111111111"


def test_get_update_and_delete_aws_connection() -> None:
    app = create_app("testing")
    client = app.test_client()

    create_response = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "210987654321",
            "aws_region": "ap-southeast-2",
        },
        headers=_auth_headers(),
    )
    connection_id = create_response.get_json()["id"]

    get_response = client.get(f"/aws-connections/{connection_id}", headers=_auth_headers())
    assert get_response.status_code == 200
    assert get_response.get_json()["aws_account_id"] == "210987654321"

    update_response = client.put(
        f"/aws-connections/{connection_id}",
        json={"connection_status": "CONNECTED"},
        headers=_auth_headers(),
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["connection_status"] == "CONNECTED"

    delete_response = client.delete(f"/aws-connections/{connection_id}", headers=_auth_headers())
    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "AWS connection deleted successfully."


def test_create_aws_connection_requires_valid_payload() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/aws-connections",
        json={"aws_account_id": "invalid", "aws_region": "bad-region", "role_arn": "not-an-arn"},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"]


def test_register_role_arn() -> None:
    app = create_app("testing")
    client = app.test_client()

    # Create connection without role ARN
    create_response = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
        },
        headers=_auth_headers(),
    )
    connection_id = create_response.get_json()["id"]

    # Register role ARN
    register_response = client.post(
        f"/aws-connections/{connection_id}/register-role-arn",
        json={"role_arn": "arn:aws:iam::123456789012:role/CloudBridgeMigrationRole"},
        headers=_auth_headers(),
    )
    assert register_response.status_code == 200
    data = register_response.get_json()
    assert data["role_arn"] == "arn:aws:iam::123456789012:role/CloudBridgeMigrationRole"
    assert data["connection_status"] == "PENDING"


def test_register_role_arn_rejects_invalid_arn() -> None:
    app = create_app("testing")
    client = app.test_client()

    create_response = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
        },
        headers=_auth_headers(),
    )
    connection_id = create_response.get_json()["id"]

    register_response = client.post(
        f"/aws-connections/{connection_id}/register-role-arn",
        json={"role_arn": "not-a-valid-arn"},
        headers=_auth_headers(),
    )
    assert register_response.status_code == 400
