from unittest.mock import MagicMock, patch

from app import create_app
from app.middleware.auth import encode_token


def _auth_headers():
    token = encode_token("test-user", "test@example.com", "Test User")
    return {"Authorization": f"Bearer {token}"}


def test_create_source_database_config() -> None:
    """Test creating a source database config with mocked AWS Secrets Manager."""
    app = create_app("testing")
    client = app.test_client()

    # Create AWS Connection first
    aws_conn_resp = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
            "role_arn": "arn:aws:iam::123456789012:role/CloudBridgeRole",
        },
        headers=_auth_headers(),
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    # Mock TCP connectivity and Secrets Manager
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True), \
         patch("app.services.secrets_manager_service.SecretManagerService.create") as mock_create:
        mock_create.return_value = {"arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:cloudbridge/test", "name": "cloudbridge/test"}

        response = client.post(
            "/database-configs",
            json={
                "name": "Production Postgres",
                "database_type": "POSTGRESQL",
                "host": "db.example.com",
                "port": 5432,
                "username": "postgres",
                "password": "super-secret-password",
                "database_name": "production_db",
                "purpose": "SOURCE",
                "aws_connection_id": aws_conn_id,
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["name"] == "Production Postgres"
    assert json_data["purpose"] == "SOURCE"
    assert json_data["secret_arn"]
    assert json_data["aws_connection_id"] == aws_conn_id


def test_create_destination_db_option_a() -> None:
    """Test creating a destination DB with existing secret, mocked AWS."""
    app = create_app("testing")
    client = app.test_client()

    aws_conn_resp = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
            "role_arn": "arn:aws:iam::123456789012:role/CloudBridgeRole",
        },
        headers=_auth_headers(),
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True), \
         patch("app.services.secrets_manager_service.SecretManagerService.validate") as mock_validate:
        mock_validate.return_value = "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-existing-db-secret"

        response = client.post(
            "/database-configs",
            json={
                "name": "Staging Postgres Existing",
                "database_type": "POSTGRESQL",
                "host": "db-staging.example.com",
                "port": 5432,
                "username": "postgres",
                "password": "placeholder-password",
                "purpose": "DESTINATION",
                "aws_connection_id": aws_conn_id,
                "secret_name": "my-existing-db-secret",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["purpose"] == "DESTINATION"


def test_create_destination_db_option_b() -> None:
    """Test creating a destination DB with provisioning config (no AWS needed)."""
    app = create_app("testing")
    client = app.test_client()

    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True):
        response = client.post(
            "/database-configs",
            json={
                "name": "RDS Aurora Target",
                "database_type": "POSTGRESQL",
                "host": "rds-target.example.com",
                "port": 5432,
                "username": "dbadmin",
                "password": "placeholder-password",
                "purpose": "DESTINATION",
                "provisioning_config": '{"instance_class": "db.t3.medium", "allocated_storage": 20}',
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["provisioning_config"] is not None
    assert json_data["secret_arn"] is None


def test_list_and_get_database_configs() -> None:
    app = create_app("testing")
    client = app.test_client()

    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True):
        client.post(
            "/database-configs",
            json={
                "name": "Test DB",
                "database_type": "MYSQL",
                "host": "db-test.example.com",
                "port": 3306,
                "username": "root",
                "password": "password",
                "purpose": "DESTINATION",
                "provisioning_config": "{}",
            },
            headers=_auth_headers(),
        )

    list_resp = client.get("/database-configs", headers=_auth_headers())
    assert list_resp.status_code == 200
    assert len(list_resp.get_json()) == 1

    db_id = list_resp.get_json()[0]["id"]
    get_resp = client.get(f"/database-configs/{db_id}", headers=_auth_headers())
    assert get_resp.status_code == 200
    assert get_resp.get_json()["name"] == "Test DB"


def test_create_database_config_requires_auth() -> None:
    """Ensure database config endpoints require authentication."""
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/database-configs",
        json={
            "name": "Test DB",
            "database_type": "MYSQL",
            "host": "db-test.example.com",
            "port": 3306,
            "username": "root",
            "password": "password",
            "purpose": "DESTINATION",
        },
    )
    assert response.status_code == 401
