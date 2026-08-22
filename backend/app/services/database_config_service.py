"""Service layer for database onboarding configuration."""

from __future__ import annotations

import logging
import socket
from datetime import datetime
from typing import Any

from flask import current_app

from app.extensions import db
from app.models.aws_connection import AWSConnection
from app.models.database_config import DatabaseConfig
from app.schemas.database_config import CreateDatabaseConfigRequest, DatabaseConfigResponse, DeleteDatabaseConfigResponse
from app.services.secrets_manager_service import SecretManagerService

logger = logging.getLogger(__name__)


class DatabaseConfigValidationError(ValueError):
    """Raised when a database config request is invalid."""


class DatabaseConfigNotFoundError(ValueError):
    """Raised when a database config cannot be located."""


def test_tcp_connectivity(host: str, port: int, timeout: int = 5) -> bool:
    """Test TCP socket reachability for the given host and port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error, OSError):
        return False


class DatabaseConfigService:
    """Coordinates database onboarding configuration persistence."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

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
                self._log_info(f"Database TCP check failed for {create_request.host}:{create_request.port}")
                raise DatabaseConfigValidationError(
                    f"Database connection test failed. Unable to reach {create_request.host}:{create_request.port} via TCP. "
                    "Confirm the database is running and listening on this port, and allow inbound traffic from the "
                    "CloudBridge backend/Render outbound IP in the RDS or EC2 security group. Public accessibility alone is not sufficient."
                )

            # 3. Persist a secret reference when the customer config is backed by AWS Secrets Manager.
            secret_arn = create_request.secret_arn
            secret_name = create_request.secret_name

            if create_request.aws_connection_id and not secret_arn and create_request.purpose == "SOURCE":
                secret = SecretManagerService.create(
                    name=f"cloudbridge/{create_request.name.lower().replace(' ', '-')}",
                    value={"username": create_request.username, "password": create_request.password or ""},
                )
                if isinstance(secret, dict):
                    secret_arn = secret.get("arn") or secret_arn
                    secret_name = secret.get("name") or secret_name
            elif create_request.aws_connection_id and secret_name and not secret_arn:
                secret_arn = SecretManagerService.validate(secret_name)

            config = DatabaseConfig(
                name=create_request.name,
                database_type=create_request.database_type,
                host=create_request.host,
                port=create_request.port,
                username=create_request.username,
                password=create_request.password or "",
                database_name=create_request.database_name,
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
        if "password" in payload:
            config.password = payload["password"] if isinstance(payload["password"], str) else ""
        if "database_name" in payload:
            config.database_name = payload["database_name"].strip() if isinstance(payload["database_name"], str) and payload["database_name"].strip() else None
        if "purpose" in payload and isinstance(payload["purpose"], str) and payload["purpose"].strip():
            config.purpose = payload["purpose"].strip().upper()
        if "aws_connection_id" in payload:
            config.aws_connection_id = payload["aws_connection_id"]
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

    def _get_existing_config(self, database_config_id: int) -> DatabaseConfig:
        config = DatabaseConfig.query.get(database_config_id)
        if config is None:
            raise DatabaseConfigNotFoundError(f"Database config {database_config_id} was not found.")
        return config

    def _log_info(self, message: str, database_config_id: int | None = None, name: str | None = None) -> None:
        _logger = self._logger or current_app.logger
        if database_config_id is not None and name is not None:
            _logger.info("%s for database config %s (%s)", message, database_config_id, name)
            return
        _logger.info(message)
