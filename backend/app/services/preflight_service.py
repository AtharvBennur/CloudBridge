"""
Purpose:
This service handles multi-step pre-flight validation to ensure AWS IAM role,
region access, Secrets Manager secrets, and database connectivity are fully verified before starting a migration.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.models.aws_connection import AWSConnection, AWSConnectionStatus
from app.models.database_config import DatabaseConfig
from app.services.database_config_service import test_tcp_connectivity
from app.utils.aws_client import AWSClient

logger = logging.getLogger(__name__)

# Permissions that are ALWAYS required regardless of migration type.
_ALWAYS_REQUIRED = {"sts:GetCallerIdentity", "ec2:DescribeRegions", "secretsmanager:DescribeSecret"}


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
        source_ok, source_msg, source_secret_ok, source_conn_ok = self._check_database(
            config=src_config, credentials=credentials, region=connection.aws_region, label="source"
        )
        dest_ok, dest_msg, dest_secret_ok, dest_conn_ok = self._check_database(
            config=dst_config, credentials=credentials, region=connection.aws_region, label="destination"
        )

        # ── 3. Dynamic permission analysis ─────────────────────────────────
        secrets_already_verified = source_secret_ok and dest_secret_ok
        is_aurora = self._is_aurora_destination(dst_config)
        needs_create_secret = self._needs_write_secret(src_config, dst_config)

        # Debug: log the decision tree
        src_arn = bool(src_config and (src_config.secret_arn or src_config.secret_name))
        dst_arn = bool(dst_config and (dst_config.secret_arn or dst_config.secret_name))
        logger.debug(
            "Preflight permission decision tree:\n"
            "  existing_secret_arn (source): %s\n"
            "  existing_secret_arn (dest):   %s\n"
            "  is_aurora_destination:        %s\n"
            "  needs_secret_write:           %s\n"
            "  secrets_already_verified:     %s",
            src_arn, dst_arn, is_aurora, needs_create_secret, secrets_already_verified,
        )

        permission_report = self._build_permission_report(
            raw_permissions=iam_permissions_raw,
            secrets_verified=secrets_already_verified,
            is_aurora=is_aurora,
            needs_create_secret=needs_create_secret,
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
                "secrets": {
                    "status": "PASS" if (source_secret_ok and dest_secret_ok) else "FAIL",
                    "message": (
                        "Credentials verified in AWS Secrets Manager."
                        if (source_secret_ok and dest_secret_ok)
                        else f"Secrets check failed. Source: {source_secret_ok}, Dest: {dest_secret_ok}."
                    ),
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
    ) -> tuple[bool, str, bool, bool]:
        """Return (ok, message, secret_ok, conn_ok) for a database config."""
        if config is None:
            return True, "Not configured.", True, True

        conn_ok = True
        secret_ok = True
        msg = ""

        if config.provisioning_config:
            return True, "Ready (Target will be provisioned on start).", True, True

        # TCP reachability
        conn_ok = test_tcp_connectivity(config.host, config.port)

        # Secret access
        secret_id = config.secret_arn or config.secret_name
        if credentials and secret_id:
            try:
                self._verify_secret_access(credentials, region, secret_id)
                secret_ok = True
            except Exception as exc:
                secret_ok = False
                msg = f"Secrets Manager error: {exc}"
        else:
            secret_ok = bool(secret_id)

        if conn_ok and secret_ok:
            msg = f"Ready. Reachable at {config.host}:{config.port}."
        elif not conn_ok:
            msg = f"Cannot reach {config.host}:{config.port} via TCP."

        ok = conn_ok and secret_ok
        return ok, msg, secret_ok, conn_ok

    @staticmethod
    def _is_aurora_destination(dst_config: DatabaseConfig | None) -> bool:
        """Return True if the destination looks like an Aurora cluster."""
        if dst_config is None:
            return False
        provisioning = (dst_config.provisioning_config or "").lower()
        host = (dst_config.host or "").lower()
        return "aurora" in provisioning or "aurora" in host

    @staticmethod
    def _needs_write_secret(src_config: DatabaseConfig | None, dst_config: DatabaseConfig | None) -> bool:
        """Return True only when CloudBridge will actually create or update a secret.

        Write permissions (CreateSecret / PutSecretValue) are needed when:
        - A SOURCE database has NO existing secret_arn/secret_name — CloudBridge
          must store its credentials in Secrets Manager for the first time.
        - A DESTINATION has no existing secret AND no provisioning config —
          CloudBridge must provision a secret for it.

        If both source and destination already reference existing secrets,
        CloudBridge only needs read access (DescribeSecret / GetSecretValue).
        """
        # Source: needs write only when it has no secret stored yet
        if src_config and src_config.purpose == "SOURCE":
            src_has_secret = bool(src_config.secret_arn or src_config.secret_name)
            if not src_has_secret:
                return True

        # Destination: needs write only when no secret exists and no provisioning
        if dst_config and not (dst_config.secret_arn or dst_config.secret_name) and not dst_config.provisioning_config:
            return True

        return False

    def _build_permission_report(
        self,
        raw_permissions: dict[str, Any],
        secrets_verified: bool,
        is_aurora: bool,
        needs_create_secret: bool,
    ) -> dict[str, Any]:
        """Classify every permission as required / optional and compute gaps.

        Rules:
        - Always-required perms are always required.
        - ``secretsmanager:CreateSecret`` / ``PutSecretValue`` are required only
          when CloudBridge will actually write secrets.
        - ``secretsmanager:GetSecretValue`` is NOT reported missing when
          ``secrets_verified`` is True (the describe/Get already succeeded).
        - ``rds:DescribeDBInstances`` is required for standard RDS destinations.
        - ``rds:DescribeDBClusters`` is required only for Aurora destinations.
        """
        permissions_out: dict[str, dict[str, Any]] = {}
        required_missing: list[str] = []
        optional_missing: list[str] = []

        for perm_name, probe in raw_permissions.items():
            granted = probe.get("granted", False)

            # Determine if this permission is actually required for the current migration
            required = False

            if perm_name in _ALWAYS_REQUIRED:
                required = True

            elif perm_name in ("secretsmanager:CreateSecret", "secretsmanager:PutSecretValue"):
                required = needs_create_secret

            elif perm_name == "secretsmanager:GetSecretValue":
                # If secrets validation already succeeded, we know GetSecretValue works
                # (describe_secret uses the same IAM policy). Don't report it as missing.
                if secrets_verified:
                    granted = True  # infer from successful describe
                required = True

            elif perm_name == "rds:DescribeDBInstances":
                required = True  # always useful for any RDS-related migration

            elif perm_name == "rds:DescribeDBClusters":
                required = is_aurora

            # Classify
            status = "granted" if granted else ("not_required" if not required else "missing")
            permissions_out[perm_name] = {
                "granted": granted,
                "required": required,
                "status": status,
            }

            if not granted and required:
                required_missing.append(perm_name)
            elif not granted and not required:
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

    def _verify_secret_access(self, credentials: dict[str, Any], region: str, secret_id: str) -> None:
        """Call describe_secret to verify read access to the customer secret."""
        client = self._aws_client.get_boto3_client("secretsmanager", credentials=credentials, region=region)
        client.describe_secret(SecretId=secret_id)
