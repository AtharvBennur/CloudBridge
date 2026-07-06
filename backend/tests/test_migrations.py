from app import create_app


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
    )

    response = client.get("/migrations")

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
    )
    migration_id = create_response.get_json()["id"]

    get_response = client.get(f"/migrations/{migration_id}")
    assert get_response.status_code == 200
    assert get_response.get_json()["job_name"] == "Orders Export"

    update_response = client.put(
        f"/migrations/{migration_id}",
        json={"status": "RUNNING", "description": "Processing"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["status"] == "RUNNING"
    assert update_response.get_json()["description"] == "Processing"

    delete_response = client.delete(f"/migrations/{migration_id}")
    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "Migration job deleted successfully."


def test_create_migration_job_requires_required_fields() -> None:
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/migrations",
        json={"job_name": "", "source_database": "", "destination_database": ""},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"]
