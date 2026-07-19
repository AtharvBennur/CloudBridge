"""Tests for the database validation pipeline."""

from unittest.mock import MagicMock, patch

from app import create_app
from app.middleware.auth import encode_token
from app.services.validators.sensitive_masker import (
    is_binary_column,
    mask_row,
    mask_value,
    should_mask_column,
)


def _auth_headers():
    token = encode_token("test-user", "test@example.com", "Test User")
    return {"Authorization": f"Bearer {token}"}


# ── Sensitive Masker Tests ──────────────────────────────────────────────────


def test_sensitive_masker_password():
    """Password columns are always fully redacted."""
    assert mask_value("password", "super_secret_123") == "********"
    assert mask_value("user_password", "abc") == "********"
    assert mask_value("pwd", "test") == "********"


def test_sensitive_masker_email():
    """Email values are partially masked."""
    result = mask_value("email", "john@gmail.com")
    assert result == "j***@gmail.com"


def test_sensitive_masker_phone():
    """Phone values are partially masked."""
    result = mask_value("phone", "9876543210")
    assert result == "98******10"


def test_sensitive_masker_numeric():
    """Salary/credit values are masked."""
    assert mask_value("salary", "95000") == "*****"
    # credit_card matches numeric patterns (contains "credit")
    assert mask_value("credit_card", "4111111111111111") == "*****"


def test_sensitive_masker_generic():
    """Non-sensitive patterns fall through to generic masking."""
    assert mask_value("first_name", "John Doe") == "********"
    assert mask_value("address", "123 Main St") == "********"


def test_sensitive_masker_null():
    """NULL values return 'NULL' string."""
    assert mask_value("password", None) == "NULL"


def test_should_mask_column():
    """Column name detection works for sensitive patterns."""
    assert should_mask_column("password") is True
    assert should_mask_column("user_email") is True
    assert should_mask_column("phone_number") is True
    assert should_mask_column("api_key") is True
    assert should_mask_column("first_name") is False
    assert should_mask_column("department") is False
    assert should_mask_column("id") is False


def test_is_binary_column():
    """Binary column type detection."""
    assert is_binary_column("bytea") is True
    assert is_binary_column("blob") is True
    assert is_binary_column("BLOB") is True
    assert is_binary_column("varbinary") is True
    assert is_binary_column("text") is False
    assert is_binary_column("integer") is False


def test_mask_row():
    """Full row masking with mixed sensitive/non-sensitive columns."""
    row = {
        "id": 1,
        "first_name": "John",
        "email": "john@gmail.com",
        "password": "secret123",
        "department": "IT",
    }
    masked, masked_cols = mask_row(row)
    assert masked["id"] == 1
    # first_name is NOT a sensitive pattern, so it's not masked
    assert masked["first_name"] == "John"
    assert masked["email"] == "j***@gmail.com"
    assert masked["password"] == "********"
    assert masked["department"] == "IT"
    assert "email" in masked_cols
    assert "password" in masked_cols
    assert "first_name" not in masked_cols


# ── Validation Endpoint Tests ───────────────────────────────────────────────


def test_validate_endpoint_requires_auth():
    """Validation endpoint requires authentication."""
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/database-configs/validate",
        json={
            "database_type": "POSTGRESQL",
            "host": "db.example.com",
            "port": 5432,
            "username": "postgres",
            "password": "secret",
            "database_name": "testdb",
            "purpose": "SOURCE",
        },
    )
    assert response.status_code == 401


def test_validate_endpoint_missing_fields():
    """Validation returns 400 for missing required fields."""
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/database-configs/validate",
        json={"database_type": "POSTGRESQL"},
        headers=_auth_headers(),
    )
    assert response.status_code == 400


@patch("app.services.database_validation_service.DatabaseValidationService._test_tcp", return_value=False)
def test_validate_source_tcp_failure(mock_tcp):
    """Source validation returns failed when TCP check fails."""
    app = create_app("testing")
    client = app.test_client()

    response = client.post(
        "/database-configs/validate",
        json={
            "database_type": "POSTGRESQL",
            "host": "unreachable.example.com",
            "port": 5432,
            "username": "postgres",
            "password": "secret",
            "database_name": "testdb",
            "purpose": "SOURCE",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["connection"] == "failed"
    assert data["checks"][0]["passed"] is False


@patch("app.services.database_validation_service.get_validator")
@patch("app.services.database_validation_service.DatabaseValidationService._test_tcp", return_value=True)
def test_postgresql_source_validation(mock_tcp, mock_get_validator):
    """Full PostgreSQL source validation with mocked connection."""
    app = create_app("testing")
    client = app.test_client()

    # Set up mock validator
    mock_validator = MagicMock()
    mock_validator.validate_connection.return_value = True
    mock_validator.database_exists.return_value = True
    mock_validator.validate_permissions.return_value = {"SELECT": True, "INSERT": True, "CREATE": True}
    mock_validator.discover_tables.return_value = ["employees", "departments"]
    mock_validator.get_table_row_count.return_value = 100
    mock_validator.fetch_sample_rows.return_value = (
        ["id", "first_name", "department", "salary"],
        [
            {"id": 1, "first_name": "John", "department": "IT", "salary": 95000},
            {"id": 2, "first_name": "Alice", "department": "HR", "salary": 85000},
        ],
    )
    mock_get_validator.return_value = mock_validator

    response = client.post(
        "/database-configs/validate",
        json={
            "database_type": "POSTGRESQL",
            "host": "db.example.com",
            "port": 5432,
            "username": "postgres",
            "password": "secret",
            "database_name": "testdb",
            "purpose": "SOURCE",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["connection"] == "success"
    assert data["database"] == "testdb"
    assert data["selectedTable"] == "employees"
    assert data["tables"] == ["employees", "departments"]
    assert data["rowCount"] == 100
    assert len(data["sampleRows"]) == 2
    assert len(data["checks"]) >= 4

    # Verify sensitive columns are masked
    assert "salary" in data["maskedColumns"]
    # Salary should be masked in sample rows
    assert data["sampleRows"][0]["salary"] == "*****"
    # first_name is not in sensitive patterns, but let's check it's in columns
    assert "first_name" in data["columns"]


@patch("app.services.database_validation_service.get_validator")
@patch("app.services.database_validation_service.DatabaseValidationService._test_tcp", return_value=True)
def test_mysql_source_validation(mock_tcp, mock_get_validator):
    """MySQL source validation with mocked connection."""
    app = create_app("testing")
    client = app.test_client()

    mock_validator = MagicMock()
    mock_validator.validate_connection.return_value = True
    mock_validator.database_exists.return_value = True
    mock_validator.validate_permissions.return_value = {"SELECT": True, "INSERT": True, "CREATE": True}
    mock_validator.discover_tables.return_value = ["users"]
    mock_validator.get_table_row_count.return_value = 50
    mock_validator.fetch_sample_rows.return_value = (
        ["id", "email", "phone"],
        [
            {"id": 1, "email": "john@gmail.com", "phone": "9876543210"},
        ],
    )
    mock_get_validator.return_value = mock_validator

    response = client.post(
        "/database-configs/validate",
        json={
            "database_type": "MYSQL",
            "host": "mysql.example.com",
            "port": 3306,
            "username": "root",
            "password": "secret",
            "database_name": "mydb",
            "purpose": "SOURCE",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["connection"] == "success"
    assert data["selectedTable"] == "users"
    # Email and phone should be masked
    assert "email" in data["maskedColumns"]
    assert "phone" in data["maskedColumns"]
    assert data["sampleRows"][0]["email"] == "j***@gmail.com"
    assert data["sampleRows"][0]["phone"] == "98******10"


@patch("app.services.database_validation_service.get_validator")
@patch("app.services.database_validation_service.DatabaseValidationService._test_tcp", return_value=True)
def test_source_validation_returns_structured_failure_when_preview_errors(mock_tcp, mock_get_validator):
    """Preview-stage exceptions should return a failed validation response, not a 500."""
    app = create_app("testing")
    client = app.test_client()

    mock_validator = MagicMock()
    mock_validator.validate_connection.return_value = True
    mock_validator.database_exists.return_value = True
    mock_validator.validate_permissions.return_value = {"SELECT": True, "INSERT": True, "CREATE": True}
    mock_validator.discover_tables.return_value = ["employees"]
    mock_validator.get_table_row_count.return_value = 100
    mock_validator.fetch_sample_rows.side_effect = Exception("Access denied for table 'employees'")
    mock_get_validator.return_value = mock_validator

    response = client.post(
        "/database-configs/validate",
        json={
            "database_type": "MYSQL",
            "host": "mysql.example.com",
            "port": 3306,
            "username": "root",
            "password": "secret",
            "database_name": "company",
            "purpose": "SOURCE",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["connection"] == "failed"
    assert data["selectedTable"] == "employees"
    assert data["tables"] == ["employees"]
    assert data["checks"][-1]["step"] == "previewing_table"
    assert "unable to preview table" in data["checks"][-1]["detail"].lower()


@patch("app.services.database_validation_service.get_validator")
@patch("app.services.database_validation_service.DatabaseValidationService._test_tcp", return_value=True)
def test_destination_validation(mock_tcp, mock_get_validator):
    """Destination validation returns permission checks."""
    app = create_app("testing")
    client = app.test_client()

    mock_validator = MagicMock()
    mock_validator.validate_connection.return_value = True
    mock_validator.database_exists.return_value = True
    mock_validator.validate_permissions.return_value = {"SELECT": True, "INSERT": True, "CREATE": True}
    mock_get_validator.return_value = mock_validator

    response = client.post(
        "/database-configs/validate",
        json={
            "database_type": "POSTGRESQL",
            "host": "dest.example.com",
            "port": 5432,
            "username": "postgres",
            "password": "secret",
            "database_name": "target_db",
            "purpose": "DESTINATION",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["connection"] == "success"
    assert data["databaseExists"] is True
    assert data["writePermission"] is True
    assert data["readPermission"] is True
    assert len(data["checks"]) >= 4


@patch("app.services.database_validation_service.get_validator")
@patch("app.services.database_validation_service.DatabaseValidationService._test_tcp", return_value=True)
def test_validate_endpoint_returns_masked_data(mock_tcp, mock_get_validator):
    """Verify that password columns are NEVER returned in sample data."""
    app = create_app("testing")
    client = app.test_client()

    mock_validator = MagicMock()
    mock_validator.validate_connection.return_value = True
    mock_validator.database_exists.return_value = True
    mock_validator.validate_permissions.return_value = {"SELECT": True}
    mock_validator.discover_tables.return_value = ["users"]
    mock_validator.get_table_row_count.return_value = 10
    mock_validator.fetch_sample_rows.return_value = (
        ["id", "username", "password_hash", "email"],
        [
            {"id": 1, "username": "admin", "password_hash": "bcrypt_hash_here", "email": "admin@test.com"},
        ],
    )
    mock_get_validator.return_value = mock_validator

    response = client.post(
        "/database-configs/validate",
        json={
            "database_type": "POSTGRESQL",
            "host": "db.example.com",
            "port": 5432,
            "username": "postgres",
            "password": "secret",
            "database_name": "testdb",
            "purpose": "SOURCE",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    # password_hash should be masked
    assert "password_hash" in data["maskedColumns"]
    assert data["sampleRows"][0]["password_hash"] == "********"
    # email should be masked
    assert data["sampleRows"][0]["email"] == "a***@test.com"
