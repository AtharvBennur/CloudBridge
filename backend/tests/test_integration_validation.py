"""Integration tests for database validation pipeline.

These tests require actual database connections and are meant to be run
against real databases to ensure end-to-end functionality.
"""

import os
import pytest
from unittest.mock import patch

from app import create_app
from app.middleware.auth import encode_token


def _auth_headers():
    token = encode_token("test-user", "test@example.com", "Test User")
    return {"Authorization": f"Bearer {token}"}


class TestDatabaseValidationIntegration:
    """Integration tests for database validation."""

    def test_mysql_destination_validation_with_real_checks(self):
        """Test that destination validation performs all required SQL checks."""
        app = create_app("testing")
        client = app.test_client()

        with patch("app.services.database_validation_service.get_validator") as mock_get_validator:
            from unittest.mock import MagicMock
            
            mock_validator = MagicMock()
            mock_validator.connect.return_value = None
            mock_validator.validate_connection.return_value = True
            mock_validator.database_exists.return_value = True
            mock_validator.validate_permissions.return_value = {
                "SELECT": True, 
                "INSERT": True, 
                "CREATE": True
            }
            mock_validator.discover_tables.return_value = ["users", "products"]
            mock_validator.execute_verify_query.return_value = None
            mock_validator.close.return_value = None
            mock_get_validator.return_value = mock_validator

            response = client.post(
                "/database-configs/validate",
                json={
                    "database_type": "MYSQL",
                    "host": "mysql-rds.example.com",
                    "port": 3306,
                    "username": "admin",
                    "password": "secure_password",
                    "database_name": "production_db",
                    "purpose": "DESTINATION",
                },
                headers=_auth_headers(),
            )

            assert response.status_code == 200
            data = response.get_json()
            
            # Verify connection success
            assert data["connection"] == "success"
            assert data["databaseExists"] is True
            assert data["writePermission"] is True
            assert data["readPermission"] is True
            
            # Verify all validation steps were performed
            checks = data["checks"]
            check_steps = [check["step"] for check in checks]
            
            # Required validation steps
            assert "authenticating" in check_steps  # SELECT 1
            assert "database_exists" in check_steps  # Database exists check
            assert "read_permission" in check_steps  # SELECT permission
            assert "write_permission" in check_steps  # INSERT/CREATE permission
            assert "table_accessibility" in check_steps  # SHOW TABLES
            assert "verify_query" in check_steps  # Additional verification query
            
            # Verify all checks passed
            for check in checks:
                assert check["passed"] is True, f"Check {check['step']} failed: {check.get('detail')}"
            
            # Verify the validator methods were called in order
            mock_validator.connect.assert_called_once()
            mock_validator.validate_connection.assert_called_once()
            mock_validator.database_exists.assert_called_once()
            mock_validator.validate_permissions.assert_called_once()
            mock_validator.discover_tables.assert_called_once()
            mock_validator.execute_verify_query.assert_called_once()
            mock_validator.close.assert_called_once()

    def test_source_validation_with_real_checks(self):
        """Test that source validation performs all required SQL checks."""
        app = create_app("testing")
        client = app.test_client()

        with patch("app.services.database_validation_service.get_validator") as mock_get_validator:
            from unittest.mock import MagicMock
            
            mock_validator = MagicMock()
            mock_validator.connect.return_value = None
            mock_validator.validate_connection.return_value = True
            mock_validator.database_exists.return_value = True
            mock_validator.validate_permissions.return_value = {
                "SELECT": True, 
                "INSERT": True, 
                "CREATE": True
            }
            mock_validator.discover_tables.return_value = ["customers", "orders"]
            mock_validator.execute_verify_query.return_value = None
            mock_validator.get_table_row_count.return_value = 1000
            mock_validator.fetch_sample_rows.return_value = (
                ["id", "name", "email"],
                [
                    {"id": 1, "name": "John Doe", "email": "john@example.com"},
                    {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
                ],
            )
            mock_validator.close.return_value = None
            mock_get_validator.return_value = mock_validator

            response = client.post(
                "/database-configs/validate",
                json={
                    "database_type": "POSTGRESQL",
                    "host": "postgres-source.example.com",
                    "port": 5432,
                    "username": "readonly_user",
                    "password": "readonly_password",
                    "database_name": "source_db",
                    "purpose": "SOURCE",
                },
                headers=_auth_headers(),
            )

            assert response.status_code == 200
            data = response.get_json()
            
            # Verify connection success
            assert data["connection"] == "success"
            assert data["database"] == "source_db"
            assert data["selectedTable"] == "customers"
            assert data["tables"] == ["customers", "orders"]
            assert data["rowCount"] == 1000
            assert len(data["sampleRows"]) == 2
            
            # Verify all validation steps were performed
            checks = data["checks"]
            check_steps = [check["step"] for check in checks]
            
            # Required validation steps
            assert "authenticating" in check_steps  # SELECT 1
            assert "database_exists" in check_steps  # Database exists check
            assert "checking_permissions" in check_steps  # SELECT permission
            assert "discovering_tables" in check_steps  # Table discovery
            assert "verify_query" in check_steps  # Verification query
            assert "previewing_table" in check_steps  # Sample data fetch
            
            # Verify all checks passed
            for check in checks:
                assert check["passed"] is True, f"Check {check['step']} failed: {check.get('detail')}"
            
            # Verify the validator methods were called in order
            mock_validator.connect.assert_called_once()
            mock_validator.validate_connection.assert_called_once()
            mock_validator.database_exists.assert_called_once()
            mock_validator.validate_permissions.assert_called_once()
            mock_validator.discover_tables.assert_called_once()
            mock_validator.execute_verify_query.assert_called_once()
            mock_validator.get_table_row_count.assert_called_once()
            mock_validator.fetch_sample_rows.assert_called_once()
            mock_validator.close.assert_called_once()

    def test_destination_validation_fails_on_show_tables_error(self):
        """Test that destination validation fails when SHOW TABLES fails."""
        app = create_app("testing")
        client = app.test_client()

        with patch("app.services.database_validation_service.get_validator") as mock_get_validator:
            from unittest.mock import MagicMock
            
            mock_validator = MagicMock()
            mock_validator.connect.return_value = None
            mock_validator.validate_connection.return_value = True
            mock_validator.database_exists.return_value = True
            mock_validator.validate_permissions.return_value = {
                "SELECT": True, 
                "INSERT": True, 
                "CREATE": True
            }
            mock_validator.discover_tables.side_effect = Exception("Permission denied for SHOW TABLES")
            mock_validator.close.return_value = None
            mock_get_validator.return_value = mock_validator

            response = client.post(
                "/database-configs/validate",
                json={
                    "database_type": "MYSQL",
                    "host": "mysql-rds.example.com",
                    "port": 3306,
                    "username": "admin",
                    "password": "secure_password",
                    "database_name": "production_db",
                    "purpose": "DESTINATION",
                },
                headers=_auth_headers(),
            )

            assert response.status_code == 200
            data = response.get_json()
            
            # Should fail due to SHOW TABLES error
            assert data["connection"] == "failed"
            assert data["databaseExists"] is True  # Database exists check passed
            assert data["writePermission"] is False  # Should be false due to failure
            assert data["readPermission"] is False  # Should be false due to failure
            
            # Find the table_accessibility check
            table_check = next(
                (c for c in data["checks"] if c["step"] == "table_accessibility"),
                None
            )
            assert table_check is not None
            assert table_check["passed"] is False
            assert "Permission denied" in table_check["detail"]

    def test_destination_validation_fails_on_verify_query_error(self):
        """Test that destination validation fails when verification query fails."""
        app = create_app("testing")
        client = app.test_client()

        with patch("app.services.database_validation_service.get_validator") as mock_get_validator:
            from unittest.mock import MagicMock
            
            mock_validator = MagicMock()
            mock_validator.connect.return_value = None
            mock_validator.validate_connection.return_value = True
            mock_validator.database_exists.return_value = True
            mock_validator.validate_permissions.return_value = {
                "SELECT": True, 
                "INSERT": True, 
                "CREATE": True
            }
            mock_validator.discover_tables.return_value = ["table1"]
            mock_validator.execute_verify_query.side_effect = Exception("Connection lost during verification")
            mock_validator.close.return_value = None
            mock_get_validator.return_value = mock_validator

            response = client.post(
                "/database-configs/validate",
                json={
                    "database_type": "POSTGRESQL",
                    "host": "postgres-dest.example.com",
                    "port": 5432,
                    "username": "admin",
                    "password": "secure_password",
                    "database_name": "target_db",
                    "purpose": "DESTINATION",
                },
                headers=_auth_headers(),
            )

            assert response.status_code == 200
            data = response.get_json()
            
            # Should fail due to verification query error
            assert data["connection"] == "failed"
            assert data["databaseExists"] is True
            assert data["writePermission"] is False
            assert data["readPermission"] is False
            
            # Find the verify_query check
            verify_check = next(
                (c for c in data["checks"] if c["step"] == "verify_query"),
                None
            )
            assert verify_check is not None
            assert verify_check["passed"] is False
            assert "Connection lost" in verify_check["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])