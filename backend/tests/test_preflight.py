from unittest.mock import patch

from app import create_app
from app.middleware.auth import encode_token


def _auth_headers():
    token = encode_token("test-user", "test@example.com", "Test User")
    return {"Authorization": f"Bearer {token}"}


def _all_granted_iam_result():
    """Return a structured IAM result where every permission is granted."""
    perms = {}
    for name in [
        "sts:GetCallerIdentity", "ec2:DescribeRegions",
        "secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue",
        "secretsmanager:CreateSecret", "secretsmanager:PutSecretValue",
        "rds:DescribeDBInstances", "rds:DescribeDBClusters",
    ]:
        required = "always" if name in ("sts:GetCallerIdentity", "ec2:DescribeRegions", "secretsmanager:DescribeSecret") else "conditional"
        perms[name] = {"granted": True, "required": required}
    return {"permissions": perms, "required_missing": []}


def test_run_preflight_success() -> None:
    """Test preflight with mocked AWS calls and TCP connectivity."""
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
        headers=_auth_headers(),
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    # 2. Onboard Source DB
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True), \
         patch("app.services.secrets_manager_service.SecretManagerService.create") as mock_create:
        mock_create.return_value = {"arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:cloudbridge/src", "name": "cloudbridge/src"}
        src_db_resp = client.post(
            "/database-configs",
            json={
                "name": "Prod MySQL",
                "database_type": "MYSQL",
                "host": "db-prod.example.com",
                "port": 3306,
                "username": "root",
                "password": "password",
                "database_name": "production_db",
                "purpose": "SOURCE",
                "aws_connection_id": aws_conn_id,
            },
            headers=_auth_headers(),
        )
    src_db_id = src_db_resp.get_json()["id"]

    # 3. Onboard Destination DB Option B (provisioning, no Aurora)
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True):
        dst_db_resp = client.post(
            "/database-configs",
            json={
                "name": "Target MySQL",
                "database_type": "MYSQL",
                "host": "db-target.example.com",
                "port": 3306,
                "username": "admin",
                "password": "password",
                "purpose": "DESTINATION",
                "provisioning_config": '{"instance_class": "db.r6g.large"}',
            },
            headers=_auth_headers(),
        )
    dst_db_id = dst_db_resp.get_json()["id"]

    # 4. Execute Pre-flight check with mocked AWS calls
    with patch("app.services.preflight_service.test_tcp_connectivity", return_value=True), \
         patch("app.utils.aws_client.AWSClient.assume_role") as mock_assume, \
         patch("app.utils.aws_client.AWSClient.validate_region_access") as mock_region, \
         patch("app.utils.aws_client.AWSClient.validate_iam_permissions") as mock_iam, \
         patch("app.services.preflight_service.PreflightService._verify_secret_access"):
        mock_assume.return_value = {
            "AccessKeyId": "AKIAEXAMPLE",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
            "Expiration": None,
        }
        mock_region.return_value = {"region": "us-east-1", "accessible": True, "mode": "live"}
        mock_iam.return_value = _all_granted_iam_result()

        response = client.post(
            "/preflight",
            json={
                "aws_connection_id": aws_conn_id,
                "source_db_id": src_db_id,
                "destination_db_id": dst_db_id,
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "READY"
    assert json_data["aws_connection"]["id"] == aws_conn_id
    assert json_data["checks"]["sts_assume_role"]["status"] == "PASS"
    assert json_data["checks"]["iam_permissions"]["status"] == "PASS"
    assert json_data["database_status"]["source"]["ok"] is True
    assert json_data["database_status"]["destination"]["ok"] is True


def test_preflight_optional_missing_still_ready() -> None:
    """Optional perms (DescribeDBClusters for non-Aurora) missing → still READY."""
    app = create_app("testing")
    client = app.test_client()

    aws_conn_resp = client.post(
        "/aws-connections",
        json={"aws_account_id": "123456789012", "aws_region": "us-east-1",
              "role_arn": "arn:aws:iam::123456789012:role/R"},
        headers=_auth_headers(),
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    # Source DB
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True), \
         patch("app.services.secrets_manager_service.SecretManagerService.create") as mc:
        mc.return_value = {"arn": "arn:a", "name": "n"}
        src_resp = client.post("/database-configs", json={
            "name": "Src", "database_type": "MYSQL", "host": "h.com", "port": 3306,
            "username": "u", "password": "p", "database_name": "src_db",
            "purpose": "SOURCE", "aws_connection_id": aws_conn_id,
        }, headers=_auth_headers())
    src_id = src_resp.get_json()["id"]

    # Destination with provisioning (no Aurora)
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True):
        dst_resp = client.post("/database-configs", json={
            "name": "Dst", "database_type": "MYSQL", "host": "d.com", "port": 3306,
            "username": "u", "password": "p", "purpose": "DESTINATION",
            "provisioning_config": "{}",
        }, headers=_auth_headers())
    dst_id = dst_resp.get_json()["id"]

    # IAM result: DescribeDBClusters NOT granted (optional for non-Aurora)
    iam_result = _all_granted_iam_result()
    iam_result["permissions"]["rds:DescribeDBClusters"]["granted"] = False

    with patch("app.services.preflight_service.test_tcp_connectivity", return_value=True), \
         patch("app.utils.aws_client.AWSClient.assume_role", return_value={
             "AccessKeyId": "A", "SecretAccessKey": "S", "SessionToken": "T", "Expiration": None}), \
         patch("app.utils.aws_client.AWSClient.validate_region_access", return_value={"region": "us-east-1", "accessible": True, "mode": "live"}), \
         patch("app.utils.aws_client.AWSClient.validate_iam_permissions", return_value=iam_result), \
         patch("app.services.preflight_service.PreflightService._verify_secret_access"):

        response = client.post("/preflight", json={
            "aws_connection_id": aws_conn_id, "source_db_id": src_id, "destination_db_id": dst_id,
        }, headers=_auth_headers())

    data = response.get_json()
    assert data["status"] == "READY", f"Expected READY but got {data['status']}: {data['summary']}"
    assert data["checks"]["iam_permissions"]["status"] == "PASS"
    # DescribeDBClusters should be in optional_missing, not required_missing
    assert "rds:DescribeDBClusters" in data["checks"]["iam_permissions"]["optional_missing"]
    assert "rds:DescribeDBClusters" not in data["checks"]["iam_permissions"]["required_missing"]


def test_preflight_required_missing_means_failed() -> None:
    """Missing always-required perm → FAILED."""
    app = create_app("testing")
    client = app.test_client()

    aws_conn_resp = client.post(
        "/aws-connections",
        json={"aws_account_id": "123456789012", "aws_region": "us-east-1",
              "role_arn": "arn:aws:iam::123456789012:role/R"},
        headers=_auth_headers(),
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    # IAM result: ec2:DescribeRegions NOT granted (always required)
    iam_result = _all_granted_iam_result()
    iam_result["permissions"]["ec2:DescribeRegions"]["granted"] = False

    with patch("app.utils.aws_client.AWSClient.assume_role", return_value={
            "AccessKeyId": "A", "SecretAccessKey": "S", "SessionToken": "T", "Expiration": None}), \
         patch("app.utils.aws_client.AWSClient.validate_region_access", return_value={"region": "us-east-1", "accessible": True, "mode": "live"}), \
         patch("app.utils.aws_client.AWSClient.validate_iam_permissions", return_value=iam_result):

        response = client.post("/preflight", json={
            "aws_connection_id": aws_conn_id,
        }, headers=_auth_headers())

    data = response.get_json()
    assert data["status"] == "FAILED"
    assert data["checks"]["iam_permissions"]["status"] == "FAIL"
    assert "ec2:DescribeRegions" in data["checks"]["iam_permissions"]["required_missing"]


def test_case_a_existing_secret_arn_write_perms_optional() -> None:
    """Case A: Source has existing secret_arn → CreateSecret/PutSecretValue are OPTIONAL."""
    app = create_app("testing")
    client = app.test_client()

    aws_conn_resp = client.post(
        "/aws-connections",
        json={"aws_account_id": "123456789012", "aws_region": "us-east-1",
              "role_arn": "arn:aws:iam::123456789012:role/R"},
        headers=_auth_headers(),
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    # Source DB with existing secret_arn (already stored in Secrets Manager)
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True), \
         patch("app.services.secrets_manager_service.SecretManagerService.create") as mc:
        mc.return_value = {"arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:existing-src", "name": "existing-src"}
        src_resp = client.post("/database-configs", json={
            "name": "Src With Secret",
            "database_type": "MYSQL",
            "host": "db.example.com",
            "port": 3306,
            "username": "root",
            "password": "pw",
            "database_name": "src_with_secret_db",
            "purpose": "SOURCE",
            "aws_connection_id": aws_conn_id,
            "secret_arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:existing-src",
        }, headers=_auth_headers())
    src_id = src_resp.get_json()["id"]

    # Destination with existing secret_name (references existing secret)
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True), \
         patch("app.services.secrets_manager_service.SecretManagerService.validate") as mv:
        mv.return_value = "arn:aws:secretsmanager:us-east-1:123456789012:secret:existing-dst-secret"
        dst_resp = client.post("/database-configs", json={
            "name": "Dst With Secret",
            "database_type": "MYSQL",
            "host": "dst.example.com",
            "port": 3306,
            "username": "admin",
            "password": "pw",
            "purpose": "DESTINATION",
            "aws_connection_id": aws_conn_id,
            "secret_name": "existing-dst-secret",
        }, headers=_auth_headers())
    dst_id = dst_resp.get_json()["id"]

    # IAM result: CreateSecret/PutSecretValue NOT granted
    iam_result = _all_granted_iam_result()
    iam_result["permissions"]["secretsmanager:CreateSecret"]["granted"] = False
    iam_result["permissions"]["secretsmanager:PutSecretValue"]["granted"] = False

    with patch("app.services.preflight_service.test_tcp_connectivity", return_value=True), \
         patch("app.utils.aws_client.AWSClient.assume_role", return_value={
             "AccessKeyId": "A", "SecretAccessKey": "S", "SessionToken": "T", "Expiration": None}), \
         patch("app.utils.aws_client.AWSClient.validate_region_access", return_value={"region": "us-east-1", "accessible": True, "mode": "live"}), \
         patch("app.utils.aws_client.AWSClient.validate_iam_permissions", return_value=iam_result), \
         patch("app.services.preflight_service.PreflightService._verify_secret_access"):

        response = client.post("/preflight", json={
            "aws_connection_id": aws_conn_id,
            "source_db_id": src_id,
            "destination_db_id": dst_id,
        }, headers=_auth_headers())

    data = response.get_json()
    # Must be READY — write perms are optional when secrets already exist
    assert data["status"] == "READY", f"Expected READY but got {data['status']}: {data['summary']}"
    assert data["checks"]["iam_permissions"]["status"] == "PASS"
    # CreateSecret/PutSecretValue must be in optional_missing, NOT required_missing
    assert "secretsmanager:CreateSecret" in data["checks"]["iam_permissions"]["optional_missing"]
    assert "secretsmanager:PutSecretValue" in data["checks"]["iam_permissions"]["optional_missing"]
    assert "secretsmanager:CreateSecret" not in data["checks"]["iam_permissions"]["required_missing"]
    assert "secretsmanager:PutSecretValue" not in data["checks"]["iam_permissions"]["required_missing"]


def test_case_b_no_secret_arn_auto_provisioning_write_perms_required() -> None:
    """Case B: Source has NO secret_arn, dest has no secret/provisioning → CreateSecret/PutSecretValue REQUIRED."""
    app = create_app("testing")
    client = app.test_client()

    aws_conn_resp = client.post(
        "/aws-connections",
        json={"aws_account_id": "123456789012", "aws_region": "us-east-1",
              "role_arn": "arn:aws:iam::123456789012:role/R"},
        headers=_auth_headers(),
    )
    aws_conn_id = aws_conn_resp.get_json()["id"]

    # Source DB WITHOUT secret_arn (CloudBridge must create the secret)
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True), \
         patch("app.services.secrets_manager_service.SecretManagerService.create") as mc:
        mc.return_value = {"arn": "arn:a", "name": "n"}
        src_resp = client.post("/database-configs", json={
            "name": "Src No Secret",
            "database_type": "MYSQL",
            "host": "db.example.com",
            "port": 3306,
            "username": "root",
            "password": "pw",
            "database_name": "src_no_secret_db",
            "purpose": "SOURCE",
            "aws_connection_id": aws_conn_id,
        }, headers=_auth_headers())
    src_id = src_resp.get_json()["id"]

    # Destination WITHOUT secret and WITHOUT provisioning (CloudBridge must provision)
    with patch("app.services.database_config_service.test_tcp_connectivity", return_value=True):
        dst_resp = client.post("/database-configs", json={
            "name": "Dst No Secret",
            "database_type": "MYSQL",
            "host": "dst.example.com",
            "port": 3306,
            "username": "admin",
            "password": "pw",
            "purpose": "DESTINATION",
            "aws_connection_id": aws_conn_id,
        }, headers=_auth_headers())
    dst_id = dst_resp.get_json()["id"]

    # IAM result: CreateSecret/PutSecretValue NOT granted
    iam_result = _all_granted_iam_result()
    iam_result["permissions"]["secretsmanager:CreateSecret"]["granted"] = False
    iam_result["permissions"]["secretsmanager:PutSecretValue"]["granted"] = False

    with patch("app.services.preflight_service.test_tcp_connectivity", return_value=True), \
         patch("app.utils.aws_client.AWSClient.assume_role", return_value={
             "AccessKeyId": "A", "SecretAccessKey": "S", "SessionToken": "T", "Expiration": None}), \
         patch("app.utils.aws_client.AWSClient.validate_region_access", return_value={"region": "us-east-1", "accessible": True, "mode": "live"}), \
         patch("app.utils.aws_client.AWSClient.validate_iam_permissions", return_value=iam_result), \
         patch("app.services.preflight_service.PreflightService._verify_secret_access"):

        response = client.post("/preflight", json={
            "aws_connection_id": aws_conn_id,
            "source_db_id": src_id,
            "destination_db_id": dst_id,
        }, headers=_auth_headers())

    data = response.get_json()
    # Must be FAILED — write perms are required when no secrets exist
    assert data["status"] == "FAILED"
    assert data["checks"]["iam_permissions"]["status"] == "FAIL"
    assert "secretsmanager:CreateSecret" in data["checks"]["iam_permissions"]["required_missing"]
    assert "secretsmanager:PutSecretValue" in data["checks"]["iam_permissions"]["required_missing"]
