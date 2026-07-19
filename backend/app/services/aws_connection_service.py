"""
Purpose:
This file contains the AWS connection business logic with real STS integration.

Why:
Routes should remain thin, while the service layer owns validation, persistence,
cross-account STS AssumeRole, and connection testing.

Architecture:
AWS Connection Routes
↓
AWS Connection Service
↓
AWS Client / SQLAlchemy Model
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from botocore.exceptions import ClientError
from flask import current_app

from app.exceptions.aws_connection import (
    AWSConnectionIntegrationError,
    AWSConnectionNotFoundError,
    AWSConnectionValidationError,
)
from app.extensions import db
from app.models.aws_connection import AWSConnection, AWSConnectionStatus
from app.schemas.aws_connection import (
    AWSConnectionResponse,
    ConnectAWSConnectionRequest,
    CreateAWSConnectionRequest,
    DeleteAWSConnectionResponse,
    RegisterRoleArnRequest,
    UpdateAWSConnectionRequest,
)
from app.utils.aws_client import AWSClient


class AWSConnectionService:
    """Coordinates AWS connection CRUD and real STS integration."""

    def __init__(self, aws_client: AWSClient | None = None, logger: Any | None = None) -> None:
        self._aws_client = aws_client or AWSClient(logger=logger)
        self._logger = logger

    def create(self, payload: dict[str, Any] | None) -> AWSConnectionResponse:
        """Validate and persist a new AWS connection.

        The Role ARN is optional at creation time.  The customer first creates the
        connection record, downloads the CloudFormation template, deploys it, and
        then registers the generated Role ARN via ``register_role_arn``.
        """
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

    def register_role_arn(self, aws_connection_id: int, payload: dict[str, Any] | None) -> AWSConnectionResponse:
        """Register the IAM Role ARN generated by the CloudFormation stack.

        This is called after the customer deploys the CloudFormation template and
        copies the Role ARN from the stack outputs.  The ARN is validated for
        correct syntax and the account ID embedded in the ARN must match the
        account ID stored on the connection record.
        """
        connection = self._get_existing_connection(aws_connection_id)

        try:
            register_request = RegisterRoleArnRequest.from_payload(payload)
        except ValueError as exc:
            raise AWSConnectionValidationError(str(exc)) from exc

        # Extract account ID from the ARN and verify it matches
        arn_account_id = self._extract_account_id_from_arn(register_request.role_arn)
        if arn_account_id and arn_account_id != connection.aws_account_id:
            raise AWSConnectionValidationError(
                f"The Role ARN belongs to account {arn_account_id} but this connection "
                f"is registered for account {connection.aws_account_id}."
            )

        connection.role_arn = register_request.role_arn
        connection.connection_status = AWSConnectionStatus.PENDING
        connection.updated_at = datetime.utcnow()
        db.session.commit()

        self._log_info("Role ARN registered for AWS connection %s", aws_connection_id)
        return AWSConnectionResponse.from_model(connection)

    def connect(self, payload: dict[str, Any] | None = None, aws_connection_id: int | None = None) -> dict[str, Any]:
        """
        Establish a real STS connection to the customer's AWS account.

        Performs AssumeRole with external ID validation, account verification,
        and region access testing.  The connection is marked CONNECTED **only**
        when the backend successfully obtains temporary credentials via
        ``sts:AssumeRole`` and verifies them with ``sts:GetCallerIdentity``.

        If the AssumeRole call fails the connection is marked FAILED and an
        error is returned to the caller.
        """
        connection_id = self._resolve_connection_id(payload, aws_connection_id)
        connection = self._get_existing_connection(connection_id)

        # Require a Role ARN before attempting STS
        if not connection.role_arn:
            raise AWSConnectionValidationError(
                "Role ARN is not set. Please register the Role ARN from the "
                "CloudFormation stack output before testing the connection."
            )

        try:
            result = self._aws_client.test_connection(
                role_arn=connection.role_arn,
                external_id=connection.external_id,
                expected_account_id=connection.aws_account_id,
                region=connection.aws_region,
            )
        except (ClientError, ValueError) as exc:
            connection.connection_status = AWSConnectionStatus.FAILED
            connection.updated_at = datetime.utcnow()
            db.session.commit()
            self._log_info("Connection test failed for AWS connection %s: %s", connection_id, exc)
            raise AWSConnectionIntegrationError(f"Connection test failed: {exc}") from exc

        # Only mark CONNECTED if the backend truly obtained a session
        if result.get("session_assumed"):
            connection.connection_status = AWSConnectionStatus.CONNECTED
            connection.last_validated_at = datetime.utcnow()
            connection.updated_at = datetime.utcnow()
            db.session.commit()
            self._log_info("Connection test passed for AWS connection %s", connection_id)
            return {
                "status": AWSConnectionStatus.CONNECTED,
                "message": "Successfully connected to customer AWS account.",
                "step": "connect",
                "aws_connection_id": connection_id,
                "session_assumed": True,
                "details": result,
            }

        # Should not happen with the current AWSClient, but guard anyway
        connection.connection_status = AWSConnectionStatus.FAILED
        connection.updated_at = datetime.utcnow()
        db.session.commit()
        raise AWSConnectionIntegrationError(
            "AssumeRole did not return a valid session. The role may not exist "
            "or the trust policy may be misconfigured."
        )

    def validate(self, payload: dict[str, Any] | None = None, aws_connection_id: int | None = None) -> dict[str, Any]:
        """Validate an existing AWS connection including IAM permissions."""
        connection_id = self._resolve_connection_id(payload, aws_connection_id)
        connection = self._get_existing_connection(connection_id)

        if not connection.role_arn:
            raise AWSConnectionValidationError(
                "Role ARN is not set. Register the Role ARN before validating permissions."
            )

        try:
            credentials = self._aws_client.assume_role(
                connection.role_arn,
                connection.external_id,
                region=connection.aws_region,
            )
            self._aws_client.verify_account_id(credentials, connection.aws_account_id, connection.aws_region)
            self._aws_client.validate_region_access(credentials, connection.aws_region)
            iam_result = self._aws_client.validate_iam_permissions(credentials, connection.aws_region)
        except (ClientError, ValueError) as exc:
            raise AWSConnectionIntegrationError(f"Validation failed: {exc}") from exc

        raw_perms = iam_result.get("permissions", {})
        # For the connection-level validate, only always-required perms are blocking.
        always_required = {k for k, v in raw_perms.items() if v.get("required") == "always"}
        missing_required = [k for k in always_required if not raw_perms[k].get("granted", False)]
        valid = len(missing_required) == 0

        # Build a flat granted/not-granted map for backward compatibility
        flat_permissions = {k: v.get("granted", False) for k, v in raw_perms.items()}

        return {
            "status": "VALID" if valid else "PARTIAL",
            "message": "All required permissions verified." if valid else f"Missing required permissions: {', '.join(missing_required)}",
            "step": "validate",
            "aws_connection_id": connection_id,
            "permissions": flat_permissions,
            "permission_details": raw_perms,
        }

    def disconnect(self, payload: dict[str, Any] | None = None, aws_connection_id: int | None = None) -> dict[str, Any]:
        """Mark an AWS connection as disconnected."""
        connection_id = self._resolve_connection_id(payload, aws_connection_id)
        connection = self._get_existing_connection(connection_id)

        connection.connection_status = AWSConnectionStatus.DISCONNECTED
        connection.updated_at = datetime.utcnow()
        db.session.commit()

        self._log_info("AWS connection disconnected", connection_id)
        return {
            "status": AWSConnectionStatus.DISCONNECTED,
            "message": "AWS connection has been disconnected.",
            "step": "disconnect",
            "aws_connection_id": connection_id,
        }

    def _resolve_connection_id(self, payload: dict[str, Any] | None, aws_connection_id: int | None) -> int:
        if aws_connection_id is not None:
            return aws_connection_id
        if payload:
            try:
                request = ConnectAWSConnectionRequest.from_payload(payload)
                return request.aws_connection_id
            except ValueError as exc:
                raise AWSConnectionValidationError(str(exc)) from exc
        raise AWSConnectionValidationError("aws_connection_id is required.")

    def _get_existing_connection(self, aws_connection_id: int) -> AWSConnection:
        """Return an existing AWS connection or raise a not-found error."""
        aws_connection = AWSConnection.query.get(aws_connection_id)
        if aws_connection is None:
            raise AWSConnectionNotFoundError(f"AWS connection {aws_connection_id} was not found.")
        return aws_connection

    @staticmethod
    def _extract_account_id_from_arn(role_arn: str) -> str | None:
        """Extract the 12-digit account ID from an IAM Role ARN."""
        match = re.search(r":iam:{1,2}(\d{12}):role/", role_arn)
        return match.group(1) if match else None

    def _log_info(self, message: str, aws_connection_id: int | None = None, aws_account_id: str | None = None) -> None:
        """Write a structured log entry through Flask's configured logger."""
        logger = self._logger or current_app.logger
        if aws_connection_id is not None and aws_account_id is not None:
            logger.info("%s for AWS connection %s (%s)", message, aws_connection_id, aws_account_id)
            return
        if aws_connection_id is not None:
            logger.info(message, aws_connection_id)
            return
        logger.info(message)
