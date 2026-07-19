"""
Purpose:
This module provides a thin AWS client wrapper for STS and identity validation.

Why:
The AWS connection service needs a reusable integration surface for AssumeRole,
account verification, region checks, and permission validation without embedding AWS
logic directly in the service layer.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class AWSClient:
    """Thin wrapper around boto3 that supports cross-account STS assumptions."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    @staticmethod
    def has_real_aws_credentials() -> bool:
        """Return True if real AWS credentials are available in the environment."""
        access_key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
        return bool(access_key and secret_key)

    def assume_role(self, role_arn: str, external_id: str, region: str | None = None) -> dict[str, Any]:
        """Assume a customer role using a supplied external ID.

        Raises ValueError when no real AWS credentials are configured or when
        the AssumeRole call fails.
        """
        if not isinstance(role_arn, str) or not role_arn.strip():
            raise ValueError("Role ARN is required.")
        if not isinstance(external_id, str) or not external_id.strip():
            raise ValueError("External ID is required.")

        if not self.has_real_aws_credentials():
            self._log("AssumeRole rejected for %s: no real AWS credentials configured", role_arn)
            raise ValueError(
                "AWS credentials are not configured on the CloudBridge server. "
                "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables "
                "to enable cross-account STS AssumeRole."
            )

        start = time.monotonic()
        try:
            client = self._get_client("sts", region=region)
            response = client.assume_role(
                RoleArn=role_arn,
                RoleSessionName="CloudBridgeSession",
                ExternalId=external_id,
            )
            credentials = response.get("Credentials", {})
        except (ClientError, BotoCoreError, NoCredentialsError) as exc:
            duration_ms = (time.monotonic() - start) * 1000
            self._log("AssumeRole failed for %s after %.0fms: %s", role_arn, duration_ms, exc)
            raise ValueError(f"Unable to assume customer role: {exc}") from exc

        if not credentials or not credentials.get("AccessKeyId"):
            raise ValueError("AssumeRole returned empty credentials — the role may not exist or trust policy is incorrect.")

        duration_ms = (time.monotonic() - start) * 1000
        self._log(
            "AssumeRole success for %s (region=%s, duration=%.0fms); credentials expire at %s",
            role_arn, region or self._default_region(), duration_ms, credentials.get("Expiration"),
        )

        return {
            "AccessKeyId": credentials.get("AccessKeyId"),
            "SecretAccessKey": credentials.get("SecretAccessKey"),
            "SessionToken": credentials.get("SessionToken"),
            "Expiration": credentials.get("Expiration"),
            "AssumedRoleUser": {"Arn": role_arn, "AssumedRoleId": "CloudBridgeRole"},
        }

    def verify_account_id(self, credentials: dict[str, Any], expected_account_id: str, region: str | None = None) -> dict[str, Any]:
        """Verify that assumed credentials map to the expected AWS account."""
        if not isinstance(expected_account_id, str) or not expected_account_id.strip():
            raise ValueError("Expected AWS account ID is required.")

        try:
            identity = self._get_client("sts", region=region, credentials=credentials).get_caller_identity()
            account_id = identity.get("Account")
        except (ClientError, BotoCoreError) as exc:
            raise ValueError(f"Unable to verify assumed AWS identity: {exc}") from exc

        if account_id and account_id != expected_account_id:
            raise ValueError(f"Expected account {expected_account_id}, got {account_id}.")

        return {"account_id": account_id or expected_account_id, "verified": True}

    def validate_region_access(self, credentials: dict[str, Any], region: str | None = None) -> dict[str, Any]:
        """Validate that the target region is accessible using temporary credentials."""
        if not isinstance(region, str) or not region.strip():
            raise ValueError("AWS region is required.")

        try:
            client = self._get_client("ec2", region=region, credentials=credentials)
            client.describe_regions(DryRun=False)
        except (ClientError, ValueError) as exc:
            raise ValueError(f"Region validation failed: {exc}") from exc

        return {"region": region, "accessible": True, "mode": "live"}

    def validate_iam_permissions(self, credentials: dict[str, Any], region: str | None = None) -> dict[str, Any]:
        """Probe every permission and return a structured result.

        Returns::

            {
                "permissions": {
                    "sts:GetCallerIdentity":  {"granted": True,  "required": "always"},
                    "ec2:DescribeRegions":    {"granted": True,  "required": "always"},
                    "secretsmanager:DescribeSecret": {"granted": True,  "required": "always"},
                    "secretsmanager:GetSecretValue": {"granted": False, "required": "conditional"},
                    "secretsmanager:CreateSecret":   {"granted": False, "required": "conditional"},
                    "secretsmanager:PutSecretValue": {"granted": False, "required": "conditional"},
                    "rds:DescribeDBInstances":  {"granted": True,  "required": "conditional"},
                    "rds:DescribeDBClusters":   {"granted": False, "required": "conditional"},
                },
                "required_missing": [],
            }

        The ``required`` tag is *not* computed here — the caller (PreflightService)
        decides which permissions are actually required for the current migration.
        """
        perms: dict[str, dict[str, Any]] = {}

        # --- STS ---
        try:
            sts = self._get_client("sts", region=region, credentials=credentials)
            sts.get_caller_identity()
            perms["sts:GetCallerIdentity"] = {"granted": True, "required": "always"}
        except Exception:
            perms["sts:GetCallerIdentity"] = {"granted": False, "required": "always"}
            # If STS identity fails nothing else will either
            return {"permissions": perms, "required_missing": ["sts:GetCallerIdentity"]}

        # --- EC2 ---
        try:
            ec2 = self._get_client("ec2", region=region, credentials=credentials)
            ec2.describe_regions(DryRun=False)
            perms["ec2:DescribeRegions"] = {"granted": True, "required": "always"}
        except Exception:
            perms["ec2:DescribeRegions"] = {"granted": False, "required": "always"}

        # --- Secrets Manager ---
        sm = self._get_client("secretsmanager", region=region, credentials=credentials)

        # DescribeSecret (probe with a non-existent secret)
        try:
            sm.describe_secret(SecretId="cloudbridge-probe-nonexistent")
            perms["secretsmanager:DescribeSecret"] = {"granted": True, "required": "always"}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            granted = code == "ResourceNotFoundException"
            perms["secretsmanager:DescribeSecret"] = {"granted": granted, "required": "always"}
        except Exception:
            perms["secretsmanager:DescribeSecret"] = {"granted": False, "required": "always"}

        # GetSecretValue (probe — ResourceNotFoundException means we have the permission)
        try:
            sm.get_secret_value(SecretId="cloudbridge-probe-nonexistent")
            perms["secretsmanager:GetSecretValue"] = {"granted": True, "required": "conditional"}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            granted = code == "ResourceNotFoundException"
            perms["secretsmanager:GetSecretValue"] = {"granted": granted, "required": "conditional"}
        except Exception:
            perms["secretsmanager:GetSecretValue"] = {"granted": False, "required": "conditional"}

        # ListSecrets — used as a proxy for CreateSecret / PutSecretValue
        # (same Resource-level "*" in the CloudFormation policy)
        try:
            sm.list_secrets(MaxResults=1)
            perms["secretsmanager:CreateSecret"] = {"granted": True, "required": "conditional"}
            perms["secretsmanager:PutSecretValue"] = {"granted": True, "required": "conditional"}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            granted = code != "AccessDeniedException"
            perms["secretsmanager:CreateSecret"] = {"granted": granted, "required": "conditional"}
            perms["secretsmanager:PutSecretValue"] = {"granted": granted, "required": "conditional"}
        except Exception:
            perms["secretsmanager:CreateSecret"] = {"granted": False, "required": "conditional"}
            perms["secretsmanager:PutSecretValue"] = {"granted": False, "required": "conditional"}

        # --- RDS ---
        rds = self._get_client("rds", region=region, credentials=credentials)

        try:
            rds.describe_db_instances()
            perms["rds:DescribeDBInstances"] = {"granted": True, "required": "conditional"}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            perms["rds:DescribeDBInstances"] = {"granted": code != "AccessDeniedException", "required": "conditional"}
        except Exception:
            perms["rds:DescribeDBInstances"] = {"granted": False, "required": "conditional"}

        try:
            rds.describe_db_clusters()
            perms["rds:DescribeDBClusters"] = {"granted": True, "required": "conditional"}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            perms["rds:DescribeDBClusters"] = {"granted": code != "AccessDeniedException", "required": "conditional"}
        except Exception:
            perms["rds:DescribeDBClusters"] = {"granted": False, "required": "conditional"}

        return {"permissions": perms, "required_missing": []}

    def test_connection(
        self,
        role_arn: str,
        external_id: str,
        expected_account_id: str,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Run the full connection verification workflow.

        Returns a dict with ``session_assumed`` indicating whether real temporary
        credentials were successfully obtained via STS AssumeRole.
        """
        credentials = self.assume_role(role_arn, external_id, region=region)
        account_result = self.verify_account_id(credentials, expected_account_id, region=region)
        region_result = self.validate_region_access(credentials, region=region)
        permissions = self.validate_iam_permissions(credentials, region=region)

        # Verify with GetCallerIdentity as final proof
        try:
            sts_client = self._get_client("sts", region=region, credentials=credentials)
            identity = sts_client.get_caller_identity()
            caller_arn = identity.get("Arn", "")
            caller_account = identity.get("Account", "")
        except Exception:
            caller_arn = ""
            caller_account = ""

        return {
            "session_assumed": True,
            "assume_role": True,
            "account_verified": account_result["verified"],
            "region_accessible": region_result["accessible"],
            "permissions": permissions,
            "caller_identity": {
                "arn": caller_arn,
                "account": caller_account,
            },
            "credentials_expires_at": (
                credentials.get("Expiration").isoformat()
                if hasattr(credentials.get("Expiration"), "isoformat")
                else credentials.get("Expiration")
            ),
        }

    def get_boto3_client(self, service_name: str, credentials: dict[str, Any] | None = None, region: str | None = None):
        return self._get_client(service_name, region=region, credentials=credentials)

    def _get_client(self, service_name: str, region: str | None = None, credentials: dict[str, Any] | None = None):
        region_name = region or self._default_region()
        if credentials is None:
            return boto3.client(service_name, region_name=region_name)

        return boto3.client(
            service_name,
            region_name=region_name,
            aws_access_key_id=credentials.get("AccessKeyId"),
            aws_secret_access_key=credentials.get("SecretAccessKey"),
            aws_session_token=credentials.get("SessionToken"),
        )

    def _log(self, message: str, *args: Any) -> None:
        if self._logger is not None:
            self._logger.info(message, *args)

    def _default_region(self) -> str:
        return os.getenv("AWS_DEFAULT_REGION", "us-east-1")
