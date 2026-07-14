from app import create_app


def test_run_preflight_simulated_success() -> None:
    app = create_app("testing")
    client = app.test_client()

    # 1. Onboard AWS Connection
    aws_conn_resp = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
            "role_arn": "arn:aws:iam::123456789012:role/CloudBridgeRole",
        },
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    # 2. Onboard Source DB
    src_db_resp = client.post(
        "/database-configs",
        json={
            "name": "Prod MySQL",
            "database_type": "MYSQL",
            "host": "simulated",
            "port": 3306,
            "username": "root",
            "password": "password",
            "purpose": "SOURCE",
            "aws_connection_id": aws_conn_id,
        },
    )
    src_db_id = src_db_resp.get_json()["id"]

    # 3. Onboard Destination DB Option B
    dst_db_resp = client.post(
        "/database-configs",
        json={
            "name": "Target Aurora MySQL",
            "database_type": "MYSQL",
            "host": "pending",
            "port": 3306,
            "username": "admin",
            "password": "password",
            "purpose": "DESTINATION",
            "provisioning_config": '{"instance_class": "db.r6g.large"}',
        },
    )
    dst_db_id = dst_db_resp.get_json()["id"]

    # 4. Execute Pre-flight check
    response = client.post(
        "/preflight",
        json={
            "aws_connection_id": aws_conn_id,
            "source_db_id": src_db_id,
            "destination_db_id": dst_db_id,
        },
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "READY"
    assert json_data["aws_connection"]["id"] == aws_conn_id
    assert json_data["checks"]["sts_assume_role"]["status"] == "PASS"
    assert json_data["checks"]["iam_permissions"]["status"] == "PASS"
    assert json_data["database_status"]["source"]["ok"] is True
    assert json_data["database_status"]["destination"]["ok"] is True
