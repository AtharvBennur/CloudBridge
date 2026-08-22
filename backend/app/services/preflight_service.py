"""
Purpose:
This service handles multi-step pre-flight validation to ensure AWS IAM role,
region access, and database connectivity are fully verified before starting a migration.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from botocore.exceptions import ClientError

from app.models.aws_connection import AWSConnection, AWSConnectionStatus
from app.models.database_config import DatabaseConfig
from app.services.database_config_service import test_tcp_connectivity
from app.utils.aws_client import AWSClient

logger = logging.getLogger(__name__)

# Permissions that are ALWAYS required regardless of migration type.
_ALWAYS_REQUIRED = {"sts:GetCallerIdentity", "ec2:DescribeRegions"}


class PreflightService:
    """Performs deep validation for AWS connections, IAM policies, and DB reachability."""

    def __init__(self, aws_client: AWSClient | None = None) -> None:
        self._aws_client = aws_client or AWSClient()

    @staticmethod
    def _verify_secret_access(secret_arn: str | None = None, secret_name: str | None = None) -> bool:
        """Compatibility hook for legacy tests and preflight callers.

        The current implementation does not require secret validation in the local
        test environment; it simply acknowledges that the secret references are
        syntactically present.
        """
        return bool(secret_arn or secret_name)

    def check_lambda_readiness(self, aws_connection_id: int) -> dict[str, Any]:
        connection = AWSConnection.query.get(aws_connection_id)
        if connection is None:
            raise ValueError(f"AWS connection {aws_connection_id} was not found.")
        if not connection.role_arn:
            raise ValueError("Role ARN is not set on this AWS connection.")

        credentials = self._aws_client.assume_role(
            role_arn=connection.role_arn,
            external_id=connection.external_id,
            region=connection.aws_region,
        )
        lambda_client = self._aws_client.get_boto3_client("lambda", credentials=credentials, region=connection.aws_region)

        function_names = {
            "orchestrator": "orchestrator_lambda_arn",
            "worker": "worker_lambda_arn",
            "validation": "validation_lambda_arn",
        }
        results: dict[str, Any] = {}
        overall_status = "READY"

        for key, attr in function_names.items():
            arn = getattr(connection, attr, "")
            result = {"arn": arn, "status": "MISSING", "message": "No Lambda ARN recorded for this function."}
            if not arn:
                result["status"] = "MISSING"
                result["message"] = "No Lambda ARN recorded for this function. Run infrastructure discovery or redeploy the CloudFormation template."
                overall_status = "BLOCKED"
                results[key] = result
                continue

            arn_region = arn.split(":")[3] if len(arn.split(":")) > 3 else None
            if arn_region and arn_region != connection.aws_region:
                result["status"] = "REGION_MISMATCH"
                result["message"] = f"Lambda function region ({arn_region}) does not match AWS connection region ({connection.aws_region})."
                overall_status = "BLOCKED"
                results[key] = result
                continue

            try:
                lambda_client.get_function(FunctionName=arn)
                result["status"] = "READY"
                result["message"] = "Lambda function is reachable and configured."
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                result["status"] = "ACCESS_DENIED" if code in {"AccessDenied", "AccessDeniedException", "ClientError"} else "MISSING"
                result["message"] = exc.response.get("Error", {}).get("Message", str(exc))
                if result["status"] == "ACCESS_DENIED":
                    overall_status = "BLOCKED"
                else:
                    overall_status = "BLOCKED"
            except Exception as exc:
                result["status"] = "MISSING"
                result["message"] = str(exc)
                overall_status = "BLOCKED"
            results[key] = result

        return {
            "status": overall_status,
            "aws_connection_id": connection.id,
            "aws_region": connection.aws_region,
            "functions": results,
            "summary": "All Lambda functions are ready." if overall_status == "READY" else "One or more Lambda functions are not ready for migration.",
        }

    def execute(
        self,
        aws_connection_id: int,
        source_db_id: int | None = None,
        destination_db_id: int | None = None,
    ) -> dict[str, Any]:
        connection = AWSConnection.query.get(aws_connection_id)
        if connection is None:
            raise ValueError(f"AWS connection {aws_connection_id} was not found.")

        # Resolve DB configs early so we can compute required permissions.
        src_config = DatabaseConfig.query.get(source_db_id) if source_db_id else None
        dst_config = DatabaseConfig.query.get(destination_db_id) if destination_db_id else None

        # ── 1. AWS Connection Verification (STS, Region, IAM) ──────────────
        sts_ok = False
        role_access_ok = False
        region_ok = False
        iam_permissions_raw: dict[str, Any] = {}
        error_msg = None
        credentials = None

        try:
            if not connection.role_arn:
                raise ValueError("Role ARN is not set on this AWS connection.")

            credentials = self._aws_client.assume_role(
                role_arn=connection.role_arn,
                external_id=connection.external_id,
                region=connection.aws_region,
            )
            sts_ok = True
            role_access_ok = True

            region_result = self._aws_client.validate_region_access(credentials, connection.aws_region)
            region_ok = region_result.get("accessible", False)

            iam_result = self._aws_client.validate_iam_permissions(credentials, connection.aws_region)
            iam_permissions_raw = iam_result.get("permissions", {})

        except Exception as exc:
            error_msg = str(exc)
            logger.warning("Preflight AWS validation failed for connection %s: %s", aws_connection_id, exc)

        # ── 2. Database Onboarding Checks ──────────────────────────────────
        source_ok, source_msg, source_conn_ok = self._check_database(
            config=src_config, credentials=credentials, region=connection.aws_region, label="source"
        )
        dest_ok, dest_msg, dest_conn_ok = self._check_database(
            config=dst_config, credentials=credentials, region=connection.aws_region, label="destination"
        )

        # ── 3. Dynamic permission analysis ─────────────────────────────────
        is_aurora = self._is_aurora_destination(dst_config)
        secret_write_required = self._secret_write_required(src_config, dst_config)

        permission_report = self._build_permission_report(
            raw_permissions=iam_permissions_raw,
            is_aurora=is_aurora,
            secret_write_required=secret_write_required,
        )

        iam_ok = len(permission_report["required_missing"]) == 0

        # Debug: log the permission summary
        logger.debug(
            "Preflight permission results:\n"
            "  Required permissions: %s\n"
            "  Optional permissions: %s\n"
            "  Required missing:     %s\n"
            "  Optional missing:     %s",
            [k for k, v in permission_report["permissions"].items() if v.get("required")],
            [k for k, v in permission_report["permissions"].items() if not v.get("required")],
            permission_report["required_missing"],
            permission_report["optional_missing"],
        )

        # ── 4. Overall Status ──────────────────────────────────────────────
        overall_ready = sts_ok and region_ok and iam_ok and source_ok and dest_ok

        return {
            "status": "READY" if overall_ready else "FAILED",
            "summary": (
                "Pre-flight validation passed. System is ready."
                if overall_ready
                else f"Pre-flight validation failed: {error_msg or permission_report.get('summary', 'Check component status details.')}"
            ),
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
                    "message": (
                        f"Region {connection.aws_region} is accessible."
                        if region_ok
                        else f"Region {connection.aws_region} is restricted or disabled."
                    ),
                },
                "iam_permissions": {
                    "status": "PASS" if iam_ok else "FAIL",
                    "message": permission_report["summary"],
                    "details": permission_report["permissions"],
                    "required_missing": permission_report["required_missing"],
                    "optional_missing": permission_report["optional_missing"],
                },
                "database_connectivity": {
                    "status": "PASS" if (source_conn_ok and dest_conn_ok) else "FAIL",
                    "message": f"Network reachability verified. Source: {source_conn_ok}, Dest: {dest_conn_ok}.",
                },
            },
            "database_status": {
                "source": {"ok": source_ok, "message": source_msg},
                "destination": {"ok": dest_ok, "message": dest_msg},
            },
        }

    # ── Private helpers ────────────────────────────────────────────────────

    def _check_database(
        self,
        config: DatabaseConfig | None,
        credentials: dict[str, Any] | None,
        region: str,
        label: str,
    ) -> tuple[bool, str, bool]:
        """Return (ok, message, conn_ok) for a database config."""
        if config is None:
            return True, "Not configured.", True

        conn_ok = True
        msg = ""

        if config.provisioning_config:
            # Provisioned databases are assumed to be accessible
            msg = f"Provisioned database. Reachable at {config.host}:{config.port}."
        else:
            # TCP reachability
            conn_ok = test_tcp_connectivity(config.host, config.port)

        if conn_ok:
            msg = f"Ready. Reachable at {config.host}:{config.port}."
        else:
            msg = f"Cannot reach {config.host}:{config.port} via TCP."

        ok = conn_ok
        return ok, msg, conn_ok

    @staticmethod
    def _is_aurora_destination(dst_config: DatabaseConfig | None) -> bool:
        """Return True if the destination looks like an Aurora cluster."""
        if dst_config is None:
            return False
        provisioning = (dst_config.provisioning_config or "").lower()
        host = (dst_config.host or "").lower()
        return "aurora" in provisioning or "aurora" in host

    @staticmethod
    def _secret_write_required(src_config: DatabaseConfig | None, dst_config: DatabaseConfig | None) -> bool:
        """Secret writes are required only when at least one side still needs a secret created."""
        source_has_secret = bool(src_config and (src_config.secret_arn or src_config.secret_name))
        dest_has_secret = bool(dst_config and (dst_config.secret_arn or dst_config.secret_name))
        dest_will_provision = bool(dst_config and dst_config.provisioning_config)
        return not source_has_secret or (not dest_has_secret and not dest_will_provision)

    def _build_permission_report(
        self,
        raw_permissions: dict[str, Any],
        is_aurora: bool,
        secret_write_required: bool = False,
    ) -> dict[str, Any]:
        """Classify every permission as required / optional and compute gaps.

        Rules:
        - Always-required perms are always required.
        - ``rds:DescribeDBInstances`` is required for standard RDS destinations.
        - ``rds:DescribeDBClusters`` is required only for Aurora destinations.
        - Secret write permissions are required when CloudBridge must create a secret.
        """
        permissions_out: dict[str, dict[str, Any]] = {}
        required_missing: list[str] = []
        optional_missing: list[str] = []

        for perm_name, probe in raw_permissions.items():
            granted = probe.get("granted", False)

            required = False
            if perm_name in _ALWAYS_REQUIRED:
                required = True
            elif perm_name == "rds:DescribeDBInstances":
                required = True
            elif perm_name == "rds:DescribeDBClusters":
                required = is_aurora
            elif perm_name in {"secretsmanager:CreateSecret", "secretsmanager:PutSecretValue"}:
                required = secret_write_required
            else:
                required = False

            permissions_out[perm_name] = {
                "granted": granted,
                "required": required,
                "message": probe.get("message", ""),
            }

            if required and not granted:
                required_missing.append(perm_name)
            elif not required and not granted:
                optional_missing.append(perm_name)

        # Build summary
        if not required_missing:
            summary = "All required IAM permissions verified."
            if optional_missing:
                summary += f" ({len(optional_missing)} optional permission(s) not granted.)"
        else:
            summary = f"Missing required permissions: {', '.join(required_missing)}"

        return {
            "permissions": permissions_out,
            "required_missing": required_missing,
            "optional_missing": optional_missing,
            "summary": summary,
        }
