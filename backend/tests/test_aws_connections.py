from app import create_app


def test_create_aws_connection_returns_created_record() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
            "role_arn": "arn:aws:iam::123456789012:role/CloudBridgeRole",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["aws_account_id"] == "123456789012"
    assert response.get_json()["connection_status"] == "PENDING"
    assert response.get_json()["external_id"]


def test_list_aws_connections_returns_collection() -> None:
    app = create_app("testing")
    client = app.test_client()

    client.post(
        "/aws-connections",
        json={
            "aws_account_id": "111111111111",
            "aws_region": "eu-west-1",
            "role_arn": "arn:aws:iam::111111111111:role/CloudBridgeRole",
        },
    )

    response = client.get("/aws-connections")

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
            "role_arn": "arn:aws:iam::210987654321:role/CloudBridgeRole",
        },
    )
    connection_id = create_response.get_json()["id"]

    get_response = client.get(f"/aws-connections/{connection_id}")
    assert get_response.status_code == 200
    assert get_response.get_json()["aws_account_id"] == "210987654321"

    update_response = client.put(
        f"/aws-connections/{connection_id}",
        json={"connection_status": "CONNECTED"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["connection_status"] == "CONNECTED"

    delete_response = client.delete(f"/aws-connections/{connection_id}")
    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "AWS connection deleted successfully."


def test_create_aws_connection_requires_valid_payload() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/aws-connections",
        json={"aws_account_id": "invalid", "aws_region": "bad-region", "role_arn": "not-an-arn"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"]
