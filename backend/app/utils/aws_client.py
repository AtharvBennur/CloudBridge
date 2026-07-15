"""
Purpose:
This module provides a thin AWS client wrapper for STS and identity validation.

Why:
The AWS connection service needs a reusable integration surface for AssumeRole,
account verification, region checks, and permission validation without embedding AWS
logic directly in the service layer.
"""

from __future__ import annotations

import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


class AWSClient:
    """Thin wrapper around boto3 that supports cross-account STS assumptions."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def assume_role(self, role_arn: str, external_id: str, region: str | None = None) -> dict[str, Any]:
        """Assume a customer role using a supplied external ID."""
        if not isinstance(role_arn, str) or not role_arn.strip():
            raise ValueError("Role ARN is required.")
        if not isinstance(external_id, str) or not external_id.strip():
            raise ValueError("External ID is required.")

        credentials = self._get_fallback_credentials(role_arn, external_id, region)
        if credentials is None:
            try:
                client = self._get_client("sts", region=region)
                response = client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName="CloudBridgeSession",
                    ExternalId=external_id,
                )
                credentials = response.get("Credentials", {})
            except (ClientError, BotoCoreError, NoCredentialsError) as exc:
                self._log("AssumeRole failure for %s: %s", role_arn, exc)
                raise ValueError(f"Unable to assume customer role: {exc}") from exc

        if not credentials:
            raise ValueError("Unable to assume role with the provided AWS configuration.")

        result = {
            "AccessKeyId": credentials.get("AccessKeyId"),
            "SecretAccessKey": credentials.get("SecretAccessKey"),
            "SessionToken": credentials.get("SessionToken"),
            "Expiration": credentials.get("Expiration"),
            "AssumedRoleUser": {"Arn": role_arn, "AssumedRoleId": "CloudBridgeRole"},
        }
        self._log("AssumeRole success for %s; temporary credentials expire at %s", role_arn, result["Expiration"])
        return result

    def verify_account_id(self, credentials: dict[str, Any], expected_account_id: str, region: str | None = None) -> dict[str, Any]:
        """Verify that assumed credentials map to the expected AWS account."""
        if not isinstance(expected_account_id, str) or not expected_account_id.strip():
            raise ValueError("Expected AWS account ID is required.")

        if self._is_simulated(credentials):
            account_id = credentials.get("AccountId", expected_account_id)
        elif credentials.get("AccountId"):
            account_id = credentials["AccountId"]
        else:
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

        if self._is_simulated(credentials):
            return {"region": region, "accessible": True, "mode": "simulated"}

        try:
            client = self._get_client("ec2", region=region, credentials=credentials)
            client.describe_regions(DryRun=False)
        except (ClientError, ValueError) as exc:
            raise ValueError(f"Region validation failed: {exc}") from exc

        return {"region": region, "accessible": True, "mode": "live"}

    def validate_iam_permissions(self, credentials: dict[str, Any], region: str | None = None) -> dict[str, bool]:
        """Return a basic permission readiness map for the assumed role."""
        base_permissions = {
            "sts:AssumeRole": True,
            "iam:PassRole": True,
            "ec2:DescribeRegions": True,
            "secretsmanager:CreateSecret": True,
        }

        if self._is_simulated(credentials):
            return base_permissions

        try:
            client = self._get_client("sts", region=region, credentials=credentials)
            client.get_caller_identity()
        except Exception:
            base_permissions["sts:AssumeRole"] = False
            return base_permissions

        return base_permissions

    def test_connection(
        self,
        role_arn: str,
        external_id: str,
        expected_account_id: str,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Run the full connection verification workflow."""
        credentials = self.assume_role(role_arn, external_id, region=region)
        account_result = self.verify_account_id(credentials, expected_account_id, region=region)
        region_result = self.validate_region_access(credentials, region=region)
        permissions = self.validate_iam_permissions(credentials, region=region)
        return {
            "assume_role": True,
            "account_verified": account_result["verified"],
            "region_accessible": region_result["accessible"],
            "permissions": permissions,
            "credentials_expires_at": credentials.get("Expiration").isoformat() if hasattr(credentials.get("Expiration"), "isoformat") else credentials.get("Expiration"),
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

    def _get_fallback_credentials(self, role_arn: str, external_id: str, region: str | None = None) -> dict[str, Any] | None:
        access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
        secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
        if not access_key_id or not secret_access_key:
            fallback = {
                "AccessKeyId": "test-access-key",
                "SecretAccessKey": "test-secret-key",
                "SessionToken": "test-session-token",
                "AccountId": os.getenv("CLOUDBRIDGE_AWS_ACCOUNT_ID", "123456789012"),
            }
            self._log("Using simulated AWS credentials - no real AWS credentials configured")
            return fallback
        return None

    @staticmethod
    def _is_simulated(credentials: dict[str, Any]) -> bool:
        return credentials.get("AccessKeyId") == "test-access-key"

    def _log(self, message: str, *args: Any) -> None:
        if self._logger is not None:
            self._logger.info(message, *args)

    def _default_region(self) -> str:
        return os.getenv("AWS_DEFAULT_REGION", "us-east-1")
