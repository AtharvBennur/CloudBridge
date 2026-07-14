"""Customer-account AWS Secrets Manager lifecycle operations."""

from __future__ import annotations

import json
from typing import Any

from app.models.aws_connection import AWSConnection
from app.utils.aws_client import AWSClient


class SecretManagerService:
    """Stores and validates database credentials only in the customer AWS account."""

    def __init__(self, aws_client: AWSClient | None = None) -> None:
        self._aws_client = aws_client or AWSClient()

    def create(self, connection: AWSConnection, name: str, value: dict[str, Any], description: str) -> dict[str, str]:
        client = self._client(connection)
        if self._simulated(client):
            return self._simulated_secret(connection, name)
        response = client.create_secret(Name=name, SecretString=json.dumps(value), Description=description)
        return {"arn": response["ARN"], "name": name}

    def update(self, connection: AWSConnection, secret_id: str, value: dict[str, Any]) -> str:
        client = self._client(connection)
        if self._simulated(client):
            return self._simulated_secret(connection, secret_id)["arn"]
        response = client.put_secret_value(SecretId=secret_id, SecretString=json.dumps(value))
        return response["ARN"]

    def retrieve(self, connection: AWSConnection, secret_id: str) -> dict[str, Any]:
        client = self._client(connection)
        if self._simulated(client):
            return {"arn": self._simulated_secret(connection, secret_id)["arn"], "value": None, "simulated": True}
        response = client.get_secret_value(SecretId=secret_id)
        return {"arn": response["ARN"], "value": json.loads(response.get("SecretString", "{}"))}

    def validate(self, connection: AWSConnection, secret_id: str) -> str:
        client = self._client(connection)
        if self._simulated(client):
            return self._simulated_secret(connection, secret_id)["arn"]
        return client.describe_secret(SecretId=secret_id)["ARN"]

    def delete(self, connection: AWSConnection, secret_id: str, recovery_window_days: int = 7) -> None:
        client = self._client(connection)
        if not self._simulated(client):
            client.delete_secret(SecretId=secret_id, RecoveryWindowInDays=recovery_window_days)

    def _client(self, connection: AWSConnection):
        credentials = self._aws_client.assume_role(connection.role_arn, connection.external_id, connection.aws_region)
        if self._aws_client._is_simulated(credentials):
            return None
        return self._aws_client._get_client("secretsmanager", connection.aws_region, credentials)

    @staticmethod
    def _simulated(client: Any) -> bool:
        return client is None

    @staticmethod
    def _simulated_secret(connection: AWSConnection, name: str) -> dict[str, str]:
        safe_name = name.removeprefix("arn:aws:secretsmanager:")
        arn = safe_name if name.startswith("arn:") else f"arn:aws:secretsmanager:{connection.aws_region}:{connection.aws_account_id}:secret:{safe_name}"
        return {"arn": arn, "name": name}
