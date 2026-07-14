from app import create_app


def test_create_source_database_config_simulated() -> None:
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
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    # Onboard Source DB
    response = client.post(
        "/database-configs",
        json={
            "name": "Production Postgres",
            "database_type": "POSTGRESQL",
            "host": "simulated-host",
            "port": 5432,
            "username": "postgres",
            "password": "super-secret-password",
            "purpose": "SOURCE",
            "aws_connection_id": aws_conn_id,
        },
    )

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["name"] == "Production Postgres"
    assert json_data["purpose"] == "SOURCE"
    assert json_data["secret_arn"]  # should generate a simulated secret ARN
    assert json_data["aws_connection_id"] == aws_conn_id


def test_create_destination_db_option_a_simulated() -> None:
    app = create_app("testing")
    client = app.test_client()

    aws_conn_resp = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
            "role_arn": "arn:aws:iam::123456789012:role/CloudBridgeRole",
        },
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    # Option A: existing secret
    response = client.post(
        "/database-configs",
        json={
            "name": "Staging Postgres Existing",
            "database_type": "POSTGRESQL",
            "host": "simulated-host",
            "port": 5432,
            "username": "postgres",
            "password": "placeholder-password",
            "purpose": "DESTINATION",
            "aws_connection_id": aws_conn_id,
            "secret_name": "my-existing-db-secret",
        },
    )

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["purpose"] == "DESTINATION"
    assert "my-existing-db-secret" in json_data["secret_arn"]


def test_create_destination_db_option_b() -> None:
    app = create_app("testing")
    client = app.test_client()

    # Option B: Provisioning config
    response = client.post(
        "/database-configs",
        json={
            "name": "RDS Aurora Target",
            "database_type": "POSTGRESQL",
            "host": "pending",
            "port": 5432,
            "username": "dbadmin",
            "password": "placeholder-password",
            "purpose": "DESTINATION",
            "provisioning_config": '{"instance_class": "db.t3.medium", "allocated_storage": 20}',
        },
    )

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["provisioning_config"] is not None
    assert json_data["secret_arn"] is None


def test_list_and_get_database_configs() -> None:
    app = create_app("testing")
    client = app.test_client()

    client.post(
        "/database-configs",
        json={
            "name": "Test DB",
            "database_type": "MYSQL",
            "host": "simulated-host",
            "port": 3306,
            "username": "root",
            "password": "password",
            "purpose": "DESTINATION",
            "provisioning_config": "{}",
        },
    )

    list_resp = client.get("/database-configs")
    assert list_resp.status_code == 200
    assert len(list_resp.get_json()) == 1

    db_id = list_resp.get_json()[0]["id"]
    get_resp = client.get(f"/database-configs/{db_id}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["name"] == "Test DB"
