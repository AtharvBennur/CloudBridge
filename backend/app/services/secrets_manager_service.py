"""Customer-account AWS Secrets Manager lifecycle operations."""

from __future__ import annotations

import json
import logging
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from app.models.aws_connection import AWSConnection
from app.utils.aws_client import AWSClient

logger = logging.getLogger(__name__)


class SecretManagerError(Exception):
    """Structured error for Secrets Manager operations."""

    def __init__(self, message: str, code: str = "SECRET_ERROR") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SecretManagerService:
    """Stores and validates database credentials only in the customer AWS account."""

    def __init__(self, aws_client: AWSClient | None = None) -> None:
        self._aws_client = aws_client or AWSClient()

    def create(self, connection: AWSConnection, name: str, value: dict[str, Any], description: str) -> dict[str, str]:
        client = self._client(connection)
        try:
            response = client.create_secret(Name=name, SecretString=json.dumps(value), Description=description)
            logger.info("Secret created: %s in account %s", name, connection.aws_account_id)
            return {"arn": response["ARN"], "name": name}
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            raise SecretManagerError(
                f"Failed to create secret '{name}': {exc}", code=error_code
            ) from exc
        except BotoCoreError as exc:
            raise SecretManagerError(
                f"AWS SDK error creating secret '{name}': {exc}", code="BOTO_ERROR"
            ) from exc

    def update(self, connection: AWSConnection, secret_id: str, value: dict[str, Any]) -> str:
        client = self._client(connection)
        try:
            response = client.put_secret_value(SecretId=secret_id, SecretString=json.dumps(value))
            logger.info("Secret updated: %s in account %s", secret_id, connection.aws_account_id)
            return response["ARN"]
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            raise SecretManagerError(
                f"Failed to update secret '{secret_id}': {exc}", code=error_code
            ) from exc
        except BotoCoreError as exc:
            raise SecretManagerError(
                f"AWS SDK error updating secret '{secret_id}': {exc}", code="BOTO_ERROR"
            ) from exc

    def retrieve(self, connection: AWSConnection, secret_id: str) -> dict[str, Any]:
        client = self._client(connection)
        try:
            response = client.get_secret_value(SecretId=secret_id)
            logger.info("Secret retrieved: %s from account %s", secret_id, connection.aws_account_id)
            return {
                "arn": response["ARN"],
                "value": json.loads(response.get("SecretString", "{}")),
            }
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                raise SecretManagerError(
                    f"Secret '{secret_id}' could not be found.", code="SECRET_NOT_FOUND"
                ) from exc
            raise SecretManagerError(
                f"Failed to retrieve secret '{secret_id}': {exc}", code=error_code
            ) from exc
        except BotoCoreError as exc:
            raise SecretManagerError(
                f"AWS SDK error retrieving secret '{secret_id}': {exc}", code="BOTO_ERROR"
            ) from exc

    def validate(self, connection: AWSConnection, secret_id: str) -> str:
        client = self._client(connection)
        try:
            return client.describe_secret(SecretId=secret_id)["ARN"]
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                raise SecretManagerError(
                    f"Secret '{secret_id}' could not be found.", code="SECRET_NOT_FOUND"
                ) from exc
            if error_code == "AccessDeniedException":
                raise SecretManagerError(
                    f"Access denied to secret '{secret_id}'. Check IAM permissions.", code="ACCESS_DENIED"
                ) from exc
            raise SecretManagerError(
                f"Failed to validate secret '{secret_id}': {exc}", code=error_code
            ) from exc
        except BotoCoreError as exc:
            raise SecretManagerError(
                f"AWS SDK error validating secret '{secret_id}': {exc}", code="BOTO_ERROR"
            ) from exc

    def delete(self, connection: AWSConnection, secret_id: str, recovery_window_days: int = 7) -> None:
        client = self._client(connection)
        try:
            client.delete_secret(SecretId=secret_id, RecoveryWindowInDays=recovery_window_days)
            logger.info("Secret scheduled for deletion: %s in account %s", secret_id, connection.aws_account_id)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            raise SecretManagerError(
                f"Failed to delete secret '{secret_id}': {exc}", code=error_code
            ) from exc
        except BotoCoreError as exc:
            raise SecretManagerError(
                f"AWS SDK error deleting secret '{secret_id}': {exc}", code="BOTO_ERROR"
            ) from exc

    def _client(self, connection: AWSConnection):
        """Obtain a Secrets Manager boto3 client via cross-account STS AssumeRole."""
        if not connection.role_arn:
            raise SecretManagerError(
                "Role ARN is not set on this AWS connection. Register the Role ARN first.",
                code="ROLE_ARN_MISSING",
            )
        try:
            credentials = self._aws_client.assume_role(
                connection.role_arn, connection.external_id, connection.aws_region
            )
        except ValueError as exc:
            raise SecretManagerError(str(exc), code="STS_ERROR") from exc
        return self._aws_client.get_boto3_client("secretsmanager", credentials=credentials, region=connection.aws_region)
