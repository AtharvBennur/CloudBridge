from unittest.mock import patch

from app import create_app
from app.middleware.auth import encode_token


def _auth_headers():
    token = encode_token("test-user", "test@example.com", "Test User")
    return {"Authorization": f"Bearer {token}"}


def test_create_migration_job_returns_created_record() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/migrations",
        json={
            "job_name": "Customer Data Sync",
            "source_database": "postgres-prod",
            "destination_database": "postgres-staging",
            "description": "Sync customer records",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    assert response.get_json()["job_name"] == "Customer Data Sync"
    assert response.get_json()["status"] == "PENDING"


def test_list_migration_jobs_returns_collection() -> None:
    app = create_app("testing")
    client = app.test_client()

    client.post(
        "/migrations",
        json={
            "job_name": "Inventory Import",
            "source_database": "mysql-prod",
            "destination_database": "mysql-dev",
        },
        headers=_auth_headers(),
    )

    response = client.get("/migrations", headers=_auth_headers())

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert response.get_json()[0]["job_name"] == "Inventory Import"


def test_get_update_and_delete_migration_job() -> None:
    app = create_app("testing")
    client = app.test_client()

    create_response = client.post(
        "/migrations",
        json={
            "job_name": "Orders Export",
            "source_database": "oracle-prod",
            "destination_database": "snowflake-dev",
        },
        headers=_auth_headers(),
    )
    migration_id = create_response.get_json()["id"]

    get_response = client.get(f"/migrations/{migration_id}", headers=_auth_headers())
    assert get_response.status_code == 200
    assert get_response.get_json()["job_name"] == "Orders Export"

    update_response = client.put(
        f"/migrations/{migration_id}",
        json={"status": "RUNNING", "description": "Processing"},
        headers=_auth_headers(),
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["status"] == "RUNNING"
    assert update_response.get_json()["description"] == "Processing"

    delete_response = client.delete(f"/migrations/{migration_id}", headers=_auth_headers())
    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "Migration job deleted successfully."


def test_create_migration_job_requires_required_fields() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/migrations",
        json={"job_name": "", "source_database": "", "destination_database": ""},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"]


def test_create_migration_with_valid_fk_references() -> None:
    """Migration creation succeeds when all FK references exist."""
    app = create_app("testing")
    client = app.test_client()

    # Create an AWS connection first
    aws_resp = client.post(
        "/aws-connections",
        json={"aws_account_id": "123456789012", "aws_region": "us-east-1",
              "role_arn": "arn:aws:iam::123456789012:role/R"},
        headers=_auth_headers(),
    )
    aws_conn_id = aws_resp.get_json()["id"]

    # Create source database config
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True), \
         patch("app.services.secrets_manager_service.SecretManagerService.create") as mc:
        mc.return_value = {"arn": "arn:a", "name": "n"}
        src_resp = client.post(
            "/database-configs",
            json={"name": "Src DB", "database_type": "MYSQL", "host": "src.example.com",
                  "port": 3306, "username": "root", "password": "pw",
                  "database_name": "src_production",
                  "purpose": "SOURCE", "aws_connection_id": aws_conn_id},
            headers=_auth_headers(),
        )
    src_id = src_resp.get_json()["id"]

    # Create destination database config
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True):
        dst_resp = client.post(
            "/database-configs",
            json={"name": "Dst DB", "database_type": "POSTGRESQL", "host": "dst.example.com",
                  "port": 5432, "username": "admin", "password": "pw",
                  "purpose": "DESTINATION", "aws_connection_id": aws_conn_id},
            headers=_auth_headers(),
        )
    dst_id = dst_resp.get_json()["id"]

    # Create migration referencing all three FK resources
    response = client.post(
        "/migrations",
        json={
            "job_name": "Full FK Migration",
            "source_database": "postgres-prod",
            "destination_database": "postgres-staging",
            "aws_connection_id": aws_conn_id,
            "source_database_config_id": src_id,
            "destination_database_config_id": dst_id,
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["job_name"] == "Full FK Migration"
    assert data["aws_connection_id"] == aws_conn_id
    assert data["source_database_config_id"] == src_id
    assert data["destination_database_config_id"] == dst_id


def test_create_migration_with_nonexistent_fk_returns_422() -> None:
    """Migration creation fails with 422 when FK references do not exist."""
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/migrations",
        json={
            "job_name": "Bad FK Migration",
            "source_database": "postgres-prod",
            "destination_database": "postgres-staging",
            "aws_connection_id": 99999,
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 422
    error_msg = response.get_json()["error"]["message"]
    assert "99999" in error_msg


def test_create_migration_with_nonexistent_source_db_config_returns_422() -> None:
    """Migration creation fails with 422 when source_database_config_id does not exist."""
    app = create_app("testing")
    client = app.test_client()

    # Create a valid AWS connection
    aws_resp = client.post(
        "/aws-connections",
        json={"aws_account_id": "123456789012", "aws_region": "us-east-1",
              "role_arn": "arn:aws:iam::123456789012:role/R"},
        headers=_auth_headers(),
    )
    aws_conn_id = aws_resp.get_json()["id"]

    response = client.post(
        "/migrations",
        json={
            "job_name": "Bad Source Config",
            "source_database": "postgres-prod",
            "destination_database": "postgres-staging",
            "aws_connection_id": aws_conn_id,
            "source_database_config_id": 88888,
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 422
    error_msg = response.get_json()["error"]["message"]
    assert "88888" in error_msg


def test_start_migration_requires_migration_id() -> None:
    """Start migration endpoint returns 400 when migration_id is missing."""
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/ecs/start-migration",
        json={},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    assert "migration_id is required" in response.get_json()["error"]["message"]


def test_start_migration_returns_404_for_nonexistent_migration() -> None:
    """Start migration endpoint returns 404 when migration does not exist."""
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/ecs/start-migration",
        json={"migration_id": 99999},
        headers=_auth_headers(),
    )

    assert response.status_code == 404
