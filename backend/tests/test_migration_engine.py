from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from app import create_app
from app.extensions import db
from app.middleware.auth import encode_token
from app.models.aws_connection import AWSConnection
from app.models.migration import MigrationJob, MigrationStatus
from app.exceptions.migration import MigrationError
from app.services.infrastructure_discovery_service import InfrastructureDiscoveryError
from app.services.lambda_migration_service import LambdaMigrationService


def _auth_headers():
    token = encode_token("test-user", "test@example.com", "Test User")
    return {"Authorization": f"Bearer {token}"}


def test_missing_arns_trigger_discovery() -> None:
    app = create_app("testing")
    with app.app_context():
        connection = AWSConnection(
            aws_account_id="123456789012",
            aws_region="us-east-1",
            role_arn="arn:aws:iam::123456789012:role/CloudBridgeMigrationRole",
            external_id="external-id-2",
            cloudformation_stack_name="cloudbridge-stack",
        )
        db.session.add(connection)
        db.session.commit()

        def fake_discover(aws_connection_id, stack_name=None):
            connection.orchestrator_lambda_arn = "arn:aws:lambda:us-east-1:123456789012:function:cloudbridge-migration-orchestrator"
            connection.worker_lambda_arn = "arn:aws:lambda:us-east-1:123456789012:function:cloudbridge-migration-worker"
            connection.validation_lambda_arn = "arn:aws:lambda:us-east-1:123456789012:function:cloudbridge-validation"
            db.session.commit()
            return connection

        with patch(
            "app.services.infrastructure_discovery_service.InfrastructureDiscoveryService.discover",
            side_effect=fake_discover,
        ):
            resolved = LambdaMigrationService()._resolve_lambda_arns(connection)

        assert resolved["orchestrator"].endswith("cloudbridge-migration-orchestrator")
        assert resolved["worker"].endswith("cloudbridge-migration-worker")
        assert resolved["validation"].endswith("cloudbridge-validation")


def test_discovery_failure_when_stack_name_missing() -> None:
    app = create_app("testing")
    with app.app_context():
        connection = AWSConnection(
            aws_account_id="123456789012",
            aws_region="us-east-1",
            role_arn="arn:aws:iam::123456789012:role/CloudBridgeMigrationRole",
            external_id="external-id-3",
            cloudformation_stack_name="",
        )
        db.session.add(connection)
        db.session.commit()

        with pytest.raises(
            InfrastructureDiscoveryError,
            match="No CloudFormation stack name recorded for this connection",
        ):
            from app.services.infrastructure_discovery_service import InfrastructureDiscoveryService

            InfrastructureDiscoveryService().discover(connection.id)


def test_region_mismatch_raises_migration_error() -> None:
    app = create_app("testing")
    with app.app_context():
        connection = AWSConnection(
            aws_account_id="123456789012",
            aws_region="us-east-1",
            role_arn="arn:aws:iam::123456789012:role/CloudBridgeMigrationRole",
            external_id="external-id-4",
            cloudformation_stack_name="cloudbridge-stack",
            orchestrator_lambda_arn="arn:aws:lambda:us-west-2:123456789012:function:cloudbridge-migration-orchestrator",
            worker_lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:cloudbridge-migration-worker",
            validation_lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:cloudbridge-validation",
        )
        db.session.add(connection)
        db.session.commit()

        with pytest.raises(
            MigrationError,
            match=r"Lambda function region \(us-west-2\) does not match AWS connection region \(us-east-1\)",
        ):
            LambdaMigrationService()._resolve_lambda_arns(connection)


def test_iam_access_denied_on_invoke_is_surfaces_aws_error_code() -> None:
    app = create_app("testing")
    client = app.test_client()

    with app.app_context():
        migration = MigrationJob(
            job_name="Test migration",
            source_database="source-db",
            destination_database="dest-db",
            status=MigrationStatus.PENDING,
            aws_connection_id=None,
            source_database_config_id=None,
            destination_database_config_id=None,
        )
        db.session.add(migration)
        db.session.commit()
        migration_id = migration.id

    error = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "not authorized"}},
        "Invoke",
    )

    with patch(
        "app.routes.migration_engine.lambda_migration_service.prepare_migration",
        return_value=object(),
    ) as prepare_mock, patch(
        "app.routes.migration_engine.lambda_migration_service.launch_migration",
        side_effect=error,
    ):
        response = client.post(
            "/migration-engine/start",
            json={"migration_id": migration_id},
            headers=_auth_headers(),
        )

    assert response.status_code == 500
    body = response.get_json()
    assert body["error"]["aws_error_code"] == "AccessDeniedException"
    assert "not authorized" in body["error"]["message"]
    prepare_mock.assert_called_once()
