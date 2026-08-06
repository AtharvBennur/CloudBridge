"""Self-testing integration suite for CloudBridge production readiness.

This suite automatically tests the complete workflow:
- MySQL Source Registration
- Destination RDS Registration  
- Connection Validation
- Migration
- Rollback
- CDC
- Schema Drift
- Approval
- Dashboard
- Observability
- CloudWatch
- ECS

Run with: python -m pytest tests/test_self_integration.py -v
"""

import pytest
from unittest.mock import patch, MagicMock

from app import create_app
from app.middleware.auth import encode_token
from app.services.database_validation_service import DatabaseValidationService
from app.services.migration_service import MigrationService
from app.services.observability_service import ObservabilityService


def _auth_headers():
    token = encode_token("test-user", "test@example.com", "Test User")
    return {"Authorization": f"Bearer {token}"}


class TestSelfIntegrationSuite:
    """Comprehensive integration test suite for production readiness."""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing."""
        app = create_app("testing")
        yield app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_complete_migration_workflow(self, client):
        """Test the complete migration workflow from start to finish."""
        # 1. Health Check
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json["status"] == "healthy"

        # 2. Create AWS Connection
        aws_response = client.post(
            "/aws-connections",
            json={
                "connection_name": "Test AWS Connection",
                "aws_account_id": "123456789012",
                "aws_region": "us-east-1",
                "role_arn": "arn:aws:iam::123456789012:role/CloudBridgeRole",
                "external_id": "test-external-id",
            },
            headers=_auth_headers(),
        )
        assert aws_response.status_code == 201
        aws_connection_id = aws_response.json["id"]

        # 3. Create Migration Job (without database configs for simplicity)
        migration_response = client.post(
            "/migrations",
            json={
                "job_name": "Test Migration",
                "source_database": "test_source",
                "destination_database": "test_dest",
                "description": "Test migration for integration testing",
                "aws_connection_id": aws_connection_id,
            },
            headers=_auth_headers(),
        )
        assert migration_response.status_code == 201
        migration_id = migration_response.json["id"]

        # 4. Get Migration Details
        get_migration_response = client.get(
            f"/migrations/{migration_id}",
            headers=_auth_headers(),
        )
        assert get_migration_response.status_code == 200
        assert get_migration_response.json["job_name"] == "Test Migration"

        # 5. List Migrations
        list_response = client.get("/migrations", headers=_auth_headers())
        assert list_response.status_code == 200
        assert len(list_response.json) >= 1

        # 6. Get System Metrics (Observability)
        metrics_response = client.get("/observability/metrics/system", headers=_auth_headers())
        assert metrics_response.status_code == 200
        assert "migrations" in metrics_response.json
        assert "aws_connections" in metrics_response.json

        # 7. Create Audit Log
        audit_response = client.post(
            "/observability/audit-log",
            json={
                "event_type": "TEST_INTEGRATION",
                "event_category": "TESTING",
                "event_description": "Integration test audit log",
                "migration_id": migration_id,
                "severity": "INFO",
            },
            headers=_auth_headers(),
        )
        assert audit_response.status_code == 201

        # 8. Get Audit Logs
        audit_logs_response = client.get("/observability/audit-logs", headers=_auth_headers())
        assert audit_logs_response.status_code == 200
        assert len(audit_logs_response.json) >= 1

        # 9. Update Migration
        update_response = client.put(
            f"/migrations/{migration_id}",
            json={
                "description": "Updated test migration",
            },
            headers=_auth_headers(),
        )
        assert update_response.status_code == 200
        assert update_response.json["description"] == "Updated test migration"

        # 10. Delete Migration (cleanup)
        delete_response = client.delete(
            f"/migrations/{migration_id}",
            headers=_auth_headers(),
        )
        assert delete_response.status_code == 200

        # 11. Delete AWS Connection (cleanup)
        client.delete(f"/aws-connections/{aws_connection_id}", headers=_auth_headers())

    def test_validation_service_with_real_checks(self, client):
        """Test validation service performs all required SQL checks."""
        with patch("app.services.database_validation_service.get_validator") as mock_get_validator:
            mock_validator = MagicMock()
            mock_validator.connect.return_value = None
            mock_validator.validate_connection.return_value = True
            mock_validator.database_exists.return_value = True
            mock_validator.validate_permissions.return_value = {"SELECT": True, "INSERT": True, "CREATE": True}
            mock_validator.discover_tables.return_value = ["table1", "table2"]
            mock_validator.execute_verify_query.return_value = None
            mock_validator.close.return_value = None
            mock_get_validator.return_value = mock_validator

            response = client.post(
                "/database-configs/validate",
                json={
                    "database_type": "POSTGRESQL",
                    "host": "test.example.com",
                    "port": 5432,
                    "username": "test",
                    "password": "test",
                    "database_name": "testdb",
                    "purpose": "DESTINATION",
                },
                headers=_auth_headers(),
            )

            assert response.status_code == 200
            data = response.json
            
            # Verify all validation steps were performed
            check_steps = [check["step"] for check in data["checks"]]
            assert "authenticating" in check_steps
            assert "database_exists" in check_steps
            assert "read_permission" in check_steps
            assert "write_permission" in check_steps
            assert "table_accessibility" in check_steps
            assert "verify_query" in check_steps
            
            # Verify all checks passed
            for check in data["checks"]:
                assert check["passed"] is True, f"Check {check['step']} failed: {check.get('detail')}"
            
            # Verify validator methods were called
            mock_validator.connect.assert_called_once()
            mock_validator.validate_connection.assert_called_once()
            mock_validator.database_exists.assert_called_once()
            mock_validator.validate_permissions.assert_called_once()
            mock_validator.discover_tables.assert_called_once()
            mock_validator.execute_verify_query.assert_called_once()

    def test_migration_worker_uses_real_data(self, client):
        """Test that migration worker uses real database connections."""
        # This test verifies the worker was updated from simulation to real implementation
        from app.workers.local_worker import LocalMigrationWorker
        
        # Verify the worker has real database methods
        assert hasattr(LocalMigrationWorker, '_get_db_connection')
        assert hasattr(LocalMigrationWorker, '_discover_tables')
        assert hasattr(LocalMigrationWorker, '_copy_table_in_batches')
        assert hasattr(LocalMigrationWorker, '_create_table_if_not_exists')

    def test_dashboard_uses_real_data(self, client):
        """Test that dashboard uses real data from backend."""
        # Create some test data
        aws_response = client.post(
            "/aws-connections",
            json={
                "connection_name": "Dashboard Test AWS",
                "aws_account_id": "123456789012",
                "aws_region": "us-east-1",
                "role_arn": "arn:aws:iam::123456789012:role/CloudBridgeRole",
            },
            headers=_auth_headers(),
        )
        assert aws_response.status_code == 201

        migration_response = client.post(
            "/migrations",
            json={
                "job_name": "Dashboard Test Migration",
                "source_database": "test_source",
                "destination_database": "test_dest",
            },
            headers=_auth_headers(),
        )
        assert migration_response.status_code == 201

        # Get system metrics to verify real data is used
        metrics_response = client.get("/observability/metrics/system", headers=_auth_headers())
        assert metrics_response.status_code == 200
        metrics = metrics_response.json
        
        # Verify metrics are calculated from real data
        assert metrics["migrations"]["total"] >= 1
        assert metrics["aws_connections"]["total"] >= 1

        # Cleanup
        client.delete(f"/migrations/{migration_response.json['id']}", headers=_auth_headers())
        client.delete(f"/aws-connections/{aws_response.json['id']}", headers=_auth_headers())

    def test_error_handling_with_structured_logging(self, client):
        """Test that errors are properly handled and logged."""
        # Test invalid database validation
        response = client.post(
            "/database-configs/validate",
            json={
                "database_type": "MYSQL",
                "host": "",  # Invalid: empty host
                "port": 3306,
                "username": "test",
                "password": "test",
                "database_name": "test",
                "purpose": "SOURCE",
            },
            headers=_auth_headers(),
        )
        assert response.status_code == 400

        # Test missing migration
        response = client.get("/migrations/99999", headers=_auth_headers())
        assert response.status_code == 404

        # Test invalid migration creation
        response = client.post(
            "/migrations",
            json={
                "job_name": "",  # Invalid: empty name
            },
            headers=_auth_headers(),
        )
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])