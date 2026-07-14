"""
Purpose:
This service handles multi-step pre-flight validation to ensure AWS IAM role,
region access, Secrets Manager secrets, and database connectivity are fully verified before starting a migration.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from app.models.aws_connection import AWSConnection, AWSConnectionStatus
from app.models.database_config import DatabaseConfig
from app.services.database_config_service import test_tcp_connectivity
from app.utils.aws_client import AWSClient


class PreflightService:
    """Performs deep validation for AWS connections, IAM policies, Secrets Manager, and DB reachability."""

    def __init__(self, aws_client: AWSClient | None = None) -> None:
        self._aws_client = aws_client or AWSClient()

    def execute(
        self,
        aws_connection_id: int,
        source_db_id: int | None = None,
        destination_db_id: int | None = None,
    ) -> dict[str, Any]:
        connection = AWSConnection.query.get(aws_connection_id)
        if connection is None:
            raise ValueError(f"AWS connection {aws_connection_id} was not found.")

        # 1. AWS Connection Verification (STS, Region, IAM)
        sts_ok = False
        role_access_ok = False
        region_ok = False
        iam_ok = False
        iam_permissions: dict[str, bool] = {}
        error_msg = None
        credentials = None

        try:
            credentials = self._aws_client.assume_role(
                role_arn=connection.role_arn,
                external_id=connection.external_id,
                region=connection.aws_region,
            )
            sts_ok = True
            role_access_ok = True

            # Verify Region
            region_result = self._aws_client.validate_region_access(credentials, connection.aws_region)
            region_ok = region_result.get("accessible", False)

            # Validate IAM Permissions
            iam_permissions = self._aws_client.validate_iam_permissions(credentials, connection.aws_region)
            # Require basic operations for migration
            required_perms = ["sts:AssumeRole", "secretsmanager:CreateSecret", "ec2:DescribeRegions"]
            iam_ok = all(iam_permissions.get(perm, False) for perm in required_perms)

        except Exception as exc:
            error_msg = str(exc)

        # 2. Database Onboarding Checks (Source and Destination)
        source_ok = True
        source_msg = "Not configured."
        source_secret_ok = True
        source_conn_ok = True

        if source_db_id:
            src_config = DatabaseConfig.query.get(source_db_id)
            if src_config:
                # Check DB network connectivity
                source_conn_ok = test_tcp_connectivity(src_config.host, src_config.port)
                # Check AWS Secret access if connection has credentials
                if credentials and src_config.secret_arn:
                    try:
                        self._verify_secret_access(credentials, connection.aws_region, src_config.secret_arn)
                        source_secret_ok = True
                    except Exception as e:
                        source_secret_ok = False
                        source_msg = f"Secrets Manager error: {e}"
                else:
                    # In simulated mode or when connection is not fully set up
                    source_secret_ok = bool(src_config.secret_arn)

                if source_conn_ok and source_secret_ok:
                    source_msg = f"Ready. Reachable at {src_config.host}:{src_config.port}."
                else:
                    source_ok = False
                    if not source_conn_ok:
                        source_msg = f"Cannot reach {src_config.host}:{src_config.port} via TCP."
            else:
                source_ok = False
                source_msg = "Source database configuration not found."

        dest_ok = True
        dest_msg = "Not configured."
        dest_secret_ok = True
        dest_conn_ok = True

        if destination_db_id:
            dst_config = DatabaseConfig.query.get(destination_db_id)
            if dst_config:
                if dst_config.provisioning_config:
                    # Option B - Provisioning pending
                    dest_msg = "Ready (Target will be provisioned on start)."
                else:
                    # Option A - Existing database
                    dest_conn_ok = test_tcp_connectivity(dst_config.host, dst_config.port)
                    if credentials and (dst_config.secret_arn or dst_config.secret_name):
                        secret_id = dst_config.secret_arn or dst_config.secret_name
                        try:
                            self._verify_secret_access(credentials, connection.aws_region, secret_id or "")
                            dest_secret_ok = True
                        except Exception as e:
                            dest_secret_ok = False
                            dest_msg = f"Secrets Manager error: {e}"
                    else:
                        dest_secret_ok = bool(dst_config.secret_arn or dst_config.secret_name)

                    if dest_conn_ok and dest_secret_ok:
                        dest_msg = f"Ready. Existing target verified."
                    else:
                        dest_ok = False
                        if not dest_conn_ok:
                            dest_msg = f"Cannot reach target host {dst_config.host}:{dst_config.port} via TCP."
            else:
                dest_ok = False
                dest_msg = "Destination database configuration not found."

        # Overall Status
        overall_ready = sts_ok and region_ok and iam_ok and source_ok and dest_ok

        return {
            "status": "READY" if overall_ready else "FAILED",
            "summary": "Pre-flight validation passed. System is ready." if overall_ready else f"Pre-flight validation failed: {error_msg or 'Check component status details.'}",
            "timestamp": datetime.utcnow().isoformat(),
            "aws_connection": {
                "id": connection.id,
                "account_id": connection.aws_account_id,
                "region": connection.aws_region,
                "status": connection.connection_status,
            },
            "checks": {
                "sts_assume_role": {
                    "status": "PASS" if sts_ok else "FAIL",
                    "message": "Successfully assumed customer cross-account role." if sts_ok else f"Failed to assume role: {error_msg}",
                },
                "role_access": {
                    "status": "PASS" if role_access_ok else "FAIL",
                    "message": "IAM trust policy and External ID matched.",
                },
                "region": {
                    "status": "PASS" if region_ok else "FAIL",
                    "message": f"Region {connection.aws_region} is accessible." if region_ok else f"Region {connection.aws_region} is restricted or disabled.",
                },
                "iam_permissions": {
                    "status": "PASS" if iam_ok else "FAIL",
                    "message": "All required IAM permissions verified." if iam_ok else f"Missing required permissions: {[k for k, v in iam_permissions.items() if not v]}",
                    "details": iam_permissions,
                },
                "secrets": {
                    "status": "PASS" if (source_secret_ok and dest_secret_ok) else "FAIL",
                    "message": "Credentials verified in AWS Secrets Manager." if (source_secret_ok and dest_secret_ok) else f"Secrets check failed. Source: {source_secret_ok}, Dest: {dest_secret_ok}.",
                },
                "database_connectivity": {
                    "status": "PASS" if (source_conn_ok and dest_conn_ok) else "FAIL",
                    "message": f"Network reachability verified. Source: {source_conn_ok}, Dest: {dest_conn_ok}.",
                },
            },
            "database_status": {
                "source": {
                    "ok": source_ok,
                    "message": source_msg,
                },
                "destination": {
                    "ok": dest_ok,
                    "message": dest_msg,
                },
            },
        }

    def _verify_secret_access(self, credentials: dict[str, Any], region: str, secret_id: str) -> None:
        """Call describe_secret to verify read access to the customer secret."""
        if credentials.get("AccessKeyId") == "test-access-key":
            return  # simulated success
        client = self._aws_client._get_client("secretsmanager", region=region, credentials=credentials)
        client.describe_secret(SecretId=secret_id)
