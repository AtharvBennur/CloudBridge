"""
Purpose:
This file contains the AWS connection business logic.

Why:
Routes should remain thin, while the service layer owns validation, persistence, and response shaping.

Architecture:
AWS Connection Routes
↓
AWS Connection Service
↓
SQLAlchemy Model
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from flask import current_app

from app.exceptions.aws_connection import AWSConnectionNotFoundError, AWSConnectionValidationError
from app.extensions import db
from app.models.aws_connection import AWSConnection, AWSConnectionStatus
from app.schemas.aws_connection import (
    AWSConnectionResponse,
    CreateAWSConnectionRequest,
    DeleteAWSConnectionResponse,
    UpdateAWSConnectionRequest,
)


class AWSConnectionService:
    """Coordinates AWS connection CRUD behavior for the current sprint."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def create(self, payload: dict[str, Any] | None) -> AWSConnectionResponse:
        """Validate and persist a new AWS connection."""
        try:
            create_request = CreateAWSConnectionRequest.from_payload(payload)
            aws_connection = AWSConnection(
                aws_account_id=create_request.aws_account_id,
                aws_region=create_request.aws_region,
                role_arn=create_request.role_arn,
                external_id=str(uuid4()),
                connection_status=AWSConnectionStatus.PENDING,
            )
            db.session.add(aws_connection)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            raise AWSConnectionValidationError(str(exc)) from exc

        self._log_info("AWS connection created", aws_connection.id, aws_connection.aws_account_id)
        return AWSConnectionResponse.from_model(aws_connection)

    def list(self) -> list[AWSConnectionResponse]:
        """Return all AWS connections in descending creation order."""
        aws_connections = AWSConnection.query.order_by(AWSConnection.created_at.desc()).all()
        self._log_info("AWS connections retrieved")
        return [AWSConnectionResponse.from_model(connection) for connection in aws_connections]

    def get(self, aws_connection_id: int) -> AWSConnectionResponse:
        """Return a single AWS connection by ID."""
        aws_connection = self._get_existing_connection(aws_connection_id)
        self._log_info("AWS connection retrieved", aws_connection.id, aws_connection.aws_account_id)
        return AWSConnectionResponse.from_model(aws_connection)

    def update(self, aws_connection_id: int, payload: dict[str, Any] | None) -> AWSConnectionResponse:
        """Update an existing AWS connection and persist the changes."""
        aws_connection = self._get_existing_connection(aws_connection_id)

        try:
            update_request = UpdateAWSConnectionRequest.from_payload(payload)
            if update_request.aws_account_id is not None:
                aws_connection.aws_account_id = update_request.aws_account_id
            if update_request.aws_region is not None:
                aws_connection.aws_region = update_request.aws_region
            if update_request.role_arn is not None:
                aws_connection.role_arn = update_request.role_arn
            if update_request.connection_status is not None:
                aws_connection.connection_status = update_request.connection_status

            aws_connection.updated_at = datetime.utcnow()
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            raise AWSConnectionValidationError(str(exc)) from exc

        self._log_info("AWS connection updated", aws_connection.id, aws_connection.aws_account_id)
        return AWSConnectionResponse.from_model(aws_connection)

    def delete(self, aws_connection_id: int) -> DeleteAWSConnectionResponse:
        """Delete an AWS connection from the data store."""
        aws_connection = self._get_existing_connection(aws_connection_id)
        db.session.delete(aws_connection)
        db.session.commit()
        self._log_info("AWS connection deleted", aws_connection.id, aws_connection.aws_account_id)
        return DeleteAWSConnectionResponse(message="AWS connection deleted successfully.")

    def connect(self) -> dict[str, Any]:
        """Return a placeholder response for future AWS STS integration."""
        return {
            "status": "PENDING",
            "message": "AWS integration will be implemented in Sprint 5.",
            "step": "connect",
        }

    def validate(self) -> dict[str, Any]:
        """Return a placeholder response for future AWS validation integration."""
        return {
            "status": "PENDING",
            "message": "AWS integration will be implemented in Sprint 5.",
            "step": "validate",
        }

    def disconnect(self) -> dict[str, Any]:
        """Return a placeholder response for future AWS disconnect integration."""
        return {
            "status": "PENDING",
            "message": "AWS integration will be implemented in Sprint 5.",
            "step": "disconnect",
        }

    def _get_existing_connection(self, aws_connection_id: int) -> AWSConnection:
        """Return an existing AWS connection or raise a not-found error."""
        aws_connection = AWSConnection.query.get(aws_connection_id)
        if aws_connection is None:
            raise AWSConnectionNotFoundError(f"AWS connection {aws_connection_id} was not found.")
        return aws_connection

    def _log_info(self, message: str, aws_connection_id: int | None = None, aws_account_id: str | None = None) -> None:
        """Write a structured log entry through Flask's configured logger."""
        logger = self._logger or current_app.logger
        if aws_connection_id is not None and aws_account_id is not None:
            logger.info("%s for AWS connection %s (%s)", message, aws_connection_id, aws_account_id)
            return
        logger.info(message)
