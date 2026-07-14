"""Service layer for database onboarding configuration."""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime
from typing import Any

from flask import current_app

from app.extensions import db
from app.models.aws_connection import AWSConnection
from app.models.database_config import DatabaseConfig
from app.schemas.database_config import CreateDatabaseConfigRequest, DatabaseConfigResponse, DeleteDatabaseConfigResponse
from app.schemas.secret import SecretReferenceRequest, SecretWriteRequest
from app.services.secrets_manager_service import SecretManagerService


class DatabaseConfigValidationError(ValueError):
    """Raised when a database config request is invalid."""


class DatabaseConfigNotFoundError(ValueError):
    """Raised when a database config cannot be located."""


def test_tcp_connectivity(host: str, port: int, timeout: int = 3) -> bool:
    """Test TCP socket reachability for the given host and port."""
    if host.lower() in ("pending", "localhost-simulated", "simulated", "simulated-host"):
        return True
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class DatabaseConfigService:
    """Coordinates database onboarding configuration persistence and AWS Secrets integration."""

    def __init__(self, logger: Any | None = None, secrets_service: SecretManagerService | None = None) -> None:
        self._logger = logger
        self._secrets_service = secrets_service or SecretManagerService()

    def create(self, payload: dict[str, Any] | None) -> DatabaseConfigResponse:
        try:
            create_request = CreateDatabaseConfigRequest.from_payload(payload)
            
            # 1. Resolve AWS Connection
            aws_connection = None
            if create_request.aws_connection_id:
                aws_connection = AWSConnection.query.get(create_request.aws_connection_id)
                if not aws_connection:
                    raise DatabaseConfigValidationError(f"AWS connection {create_request.aws_connection_id} was not found.")

            # 2. Test database socket reachability
            connected = test_tcp_connectivity(create_request.host, create_request.port)
            if not connected:
                is_simulated = True
                if create_request.aws_connection_id:
                    is_simulated = not (os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
                if not is_simulated:
                    raise DatabaseConfigValidationError(
                        f"Database connection test failed. Unable to reach {create_request.host}:{create_request.port} via TCP."
                    )
                else:
                    self._log_info(f"Database check failed for {create_request.host}:{create_request.port}, bypassed in simulated mode.")

            # 3. Store credentials or validate existing secret
            secret_arn = create_request.secret_arn
            secret_name = create_request.secret_name

            if create_request.purpose == "SOURCE":
                if not aws_connection:
                    raise DatabaseConfigValidationError("aws_connection_id is required to onboard a source database.")
                try:
                    secret_arn, secret_name = self._store_secret_in_aws(
                        aws_connection=aws_connection,
                        db_name=create_request.name,
                        db_type=create_request.database_type,
                        host=create_request.host,
                        port=create_request.port,
                        username=create_request.username,
                        password=create_request.password or ""
                    )
                    self._log_info(f"Stored database password in AWS Secrets Manager: {secret_arn}")
                except Exception as exc:
                    raise DatabaseConfigValidationError(f"AWS Secrets Manager error: {exc}") from exc

            elif create_request.purpose == "DESTINATION":
                if create_request.secret_arn or create_request.secret_name:
                    if not aws_connection:
                        raise DatabaseConfigValidationError("aws_connection_id is required to validate destination database secret.")
                    try:
                        secret_id = create_request.secret_arn or create_request.secret_name
                        secret_arn = self._validate_existing_secret_in_aws(aws_connection, secret_id or "")
                        self._log_info(f"Validated existing destination database secret: {secret_arn}")
                    except Exception as exc:
                        raise DatabaseConfigValidationError(f"AWS Secrets Manager validation failed: {exc}") from exc

            config = DatabaseConfig(
                name=create_request.name,
                database_type=create_request.database_type,
                host=create_request.host,
                port=create_request.port,
                username=create_request.username,
                purpose=create_request.purpose,
                aws_connection_id=create_request.aws_connection_id,
                secret_arn=secret_arn,
                secret_name=secret_name,
                provisioning_config=create_request.provisioning_config,
            )
            db.session.add(config)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            raise DatabaseConfigValidationError(str(exc)) from exc

        self._log_info("Database config created", config.id, config.name)
        return DatabaseConfigResponse.from_model(config)

    def list(self) -> list[DatabaseConfigResponse]:
        configs = DatabaseConfig.query.order_by(DatabaseConfig.created_at.desc()).all()
        return [DatabaseConfigResponse.from_model(config) for config in configs]

    def get(self, database_config_id: int) -> DatabaseConfigResponse:
        config = self._get_existing_config(database_config_id)
        return DatabaseConfigResponse.from_model(config)

    def update(self, database_config_id: int, payload: dict[str, Any] | None) -> DatabaseConfigResponse:
        config = self._get_existing_config(database_config_id)
        if payload is None:
            return DatabaseConfigResponse.from_model(config)
        if not isinstance(payload, dict):
            raise DatabaseConfigValidationError("Request body must be a JSON object.")

        if "name" in payload and isinstance(payload["name"], str) and payload["name"].strip():
            config.name = payload["name"].strip()
        if "host" in payload and isinstance(payload["host"], str) and payload["host"].strip():
            config.host = payload["host"].strip()
        if "port" in payload and isinstance(payload["port"], int) and payload["port"] > 0:
            config.port = payload["port"]
        if "username" in payload and isinstance(payload["username"], str) and payload["username"].strip():
            config.username = payload["username"].strip()
        if "purpose" in payload and isinstance(payload["purpose"], str) and payload["purpose"].strip():
            config.purpose = payload["purpose"].strip().upper()
        if "aws_connection_id" in payload:
            config.aws_connection_id = payload["aws_connection_id"]
        if "secret_arn" in payload:
            config.secret_arn = payload["secret_arn"].strip() if isinstance(payload["secret_arn"], str) and payload["secret_arn"].strip() else None
        if "secret_name" in payload:
            config.secret_name = payload["secret_name"].strip() if isinstance(payload["secret_name"], str) and payload["secret_name"].strip() else None
        if "provisioning_config" in payload:
            config.provisioning_config = payload["provisioning_config"] if isinstance(payload["provisioning_config"], str) else None

        config.updated_at = datetime.utcnow()
        db.session.commit()
        return DatabaseConfigResponse.from_model(config)

    def delete(self, database_config_id: int) -> DeleteDatabaseConfigResponse:
        config = self._get_existing_config(database_config_id)
        db.session.delete(config)
        db.session.commit()
        return DeleteDatabaseConfigResponse(message="Database configuration deleted successfully.")

    def create_secret(self, aws_connection_id: int, payload: dict[str, Any] | None) -> dict[str, str]:
        try:
            request = SecretWriteRequest.from_payload(payload)
        except ValueError as exc:
            raise DatabaseConfigValidationError(str(exc)) from exc
        connection = self._get_connection(aws_connection_id)
        result = self._secrets_service.create(connection, request.name, request.value, request.description)
        self._log_info("Secret created in customer AWS Secrets Manager")
        return result

    def update_secret(self, aws_connection_id: int, secret_id: str, payload: dict[str, Any] | None) -> dict[str, str]:
        try:
            request = SecretWriteRequest.from_payload(payload)
        except ValueError as exc:
            raise DatabaseConfigValidationError(str(exc)) from exc
        arn = self._secrets_service.update(self._get_connection(aws_connection_id), secret_id, request.value)
        self._log_info("Secret updated in customer AWS Secrets Manager")
        return {"arn": arn}

    def validate_secret(self, aws_connection_id: int, payload: dict[str, Any] | None) -> dict[str, str]:
        try:
            request = SecretReferenceRequest.from_payload(payload)
        except ValueError as exc:
            raise DatabaseConfigValidationError(str(exc)) from exc
        arn = self._secrets_service.validate(self._get_connection(aws_connection_id), request.secret_id)
        self._log_info("Secret validated in customer AWS Secrets Manager")
        return {"arn": arn, "status": "VALID"}

    def delete_secret(self, aws_connection_id: int, secret_id: str) -> None:
        self._secrets_service.delete(self._get_connection(aws_connection_id), secret_id)
        self._log_info("Secret scheduled for deletion in customer AWS Secrets Manager")

    @staticmethod
    def _get_connection(aws_connection_id: int) -> AWSConnection:
        connection = AWSConnection.query.get(aws_connection_id)
        if connection is None:
            raise DatabaseConfigNotFoundError(f"AWS connection {aws_connection_id} was not found.")
        return connection

    def _get_existing_config(self, database_config_id: int) -> DatabaseConfig:
        config = DatabaseConfig.query.get(database_config_id)
        if config is None:
            raise DatabaseConfigNotFoundError(f"Database config {database_config_id} was not found.")
        return config

    def _store_secret_in_aws(self, aws_connection, db_name: str, db_type: str, host: str, port: int, username: str, password: str) -> tuple[str, str]:
        secret_payload = {
            "engine": db_type.lower(),
            "host": host,
            "port": port,
            "username": username,
            "password": password
        }
        secret_name = f"cloudbridge/db-config/{db_name.lower().replace(' ', '-')}-{int(datetime.utcnow().timestamp())}"
        response = self._secrets_service.create(
            aws_connection, secret_name, secret_payload, f"Database credentials for CloudBridge: {db_name}"
        )
        return response["arn"], response["name"]

    def _validate_existing_secret_in_aws(self, aws_connection, secret_id: str) -> str:
        return self._secrets_service.validate(aws_connection, secret_id)

    def _log_info(self, message: str, database_config_id: int | None = None, name: str | None = None) -> None:
        logger = current_app.logger
        if database_config_id is not None and name is not None:
            logger.info("%s for database config %s (%s)", message, database_config_id, name)
            return
        logger.info(message)
