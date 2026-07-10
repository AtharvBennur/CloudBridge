"""
Purpose:
This file defines the request and response schemas for AWS connection endpoints.

Why:
Schemas make the API contract explicit and keep validation logic readable and testable.

Architecture:
AWS Connection Routes
↓
AWS Connection Service
↓
AWS Connection Model
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.models.aws_connection import AWSConnection, AWSConnectionStatus


class AWSConnectionValidation:
    """Reusable validation helpers for AWS connection payloads."""

    AWS_ACCOUNT_ID_PATTERN = re.compile(r"^\d{12}$")
    ROLE_ARN_PATTERN = re.compile(r"^arn:aws(?:-[a-z]+)?:iam::\d{12}:role/.+")
    REGION_PATTERN = re.compile(r"^[a-z]{2}(?:-[a-z]+){1,3}-\d+$")

    @classmethod
    def validate_aws_account_id(cls, value: Any) -> str:
        """Validate the AWS account ID format."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("AWS Account ID is required.")
        normalized = value.strip()
        if not cls.AWS_ACCOUNT_ID_PATTERN.fullmatch(normalized):
            raise ValueError("AWS Account ID must be a 12-digit numeric string.")
        return normalized

    @classmethod
    def validate_aws_region(cls, value: Any) -> str:
        """Validate the AWS region format."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("AWS Region is required.")
        normalized = value.strip()
        if not cls.REGION_PATTERN.fullmatch(normalized):
            raise ValueError("AWS Region must follow the pattern like us-east-1.")
        return normalized

    @classmethod
    def validate_role_arn(cls, value: Any) -> str:
        """Validate the role ARN format."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Role ARN is required.")
        normalized = value.strip()
        if not cls.ROLE_ARN_PATTERN.fullmatch(normalized):
            raise ValueError("Role ARN must be a valid AWS IAM role ARN.")
        return normalized

    @classmethod
    def validate_external_id(cls, value: Any) -> str:
        """Validate an external ID value and ensure it is a UUID."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("External ID is required.")
        normalized = value.strip()
        try:
            UUID(normalized)
        except ValueError as exc:
            raise ValueError("External ID must be a valid UUID.") from exc
        return normalized


@dataclass(frozen=True)
class CreateAWSConnectionRequest:
    """Represents the payload required to create a new AWS connection."""

    aws_account_id: str
    aws_region: str
    role_arn: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "CreateAWSConnectionRequest":
        """Convert raw JSON into a validated creation request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        aws_account_id = AWSConnectionValidation.validate_aws_account_id(payload.get("aws_account_id"))
        aws_region = AWSConnectionValidation.validate_aws_region(payload.get("aws_region"))
        role_arn = AWSConnectionValidation.validate_role_arn(payload.get("role_arn"))

        return cls(
            aws_account_id=aws_account_id,
            aws_region=aws_region,
            role_arn=role_arn,
        )


@dataclass(frozen=True)
class UpdateAWSConnectionRequest:
    """Represents the payload used to update an existing AWS connection."""

    aws_account_id: str | None = None
    aws_region: str | None = None
    role_arn: str | None = None
    connection_status: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "UpdateAWSConnectionRequest":
        """Convert raw JSON into a validated update request object."""
        if payload is None:
            return cls()

        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        aws_account_id = payload.get("aws_account_id")
        aws_region = payload.get("aws_region")
        role_arn = payload.get("role_arn")
        connection_status = payload.get("connection_status")

        if aws_account_id is not None:
            aws_account_id = AWSConnectionValidation.validate_aws_account_id(aws_account_id)

        if aws_region is not None:
            aws_region = AWSConnectionValidation.validate_aws_region(aws_region)

        if role_arn is not None:
            role_arn = AWSConnectionValidation.validate_role_arn(role_arn)

        if connection_status is not None:
            if not isinstance(connection_status, str) or not connection_status.strip():
                raise ValueError("Connection status must be a non-empty string.")
            normalized_status = connection_status.strip().upper()
            if normalized_status not in AWSConnectionStatus.VALUES:
                raise ValueError("Connection status must be one of: PENDING, CONNECTED, DISCONNECTED.")
            connection_status = normalized_status

        return cls(
            aws_account_id=aws_account_id,
            aws_region=aws_region,
            role_arn=role_arn,
            connection_status=connection_status,
        )


@dataclass(frozen=True)
class AWSConnectionResponse:
    """Represents the structured JSON returned by AWS connection endpoints."""

    id: int
    aws_account_id: str
    aws_region: str
    role_arn: str
    external_id: str
    connection_status: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        return {
            "id": self.id,
            "aws_account_id": self.aws_account_id,
            "aws_region": self.aws_region,
            "role_arn": self.role_arn,
            "external_id": self.external_id,
            "connection_status": self.connection_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_model(cls, connection: AWSConnection) -> "AWSConnectionResponse":
        """Build a response DTO from a persisted AWS connection."""
        return cls(
            id=connection.id,
            aws_account_id=connection.aws_account_id,
            aws_region=connection.aws_region,
            role_arn=connection.role_arn,
            external_id=connection.external_id,
            connection_status=connection.connection_status,
            created_at=connection.created_at.isoformat() if connection.created_at else "",
            updated_at=connection.updated_at.isoformat() if connection.updated_at else "",
        )


@dataclass(frozen=True)
class DeleteAWSConnectionResponse:
    """Represents the response returned after an AWS connection delete operation."""

    message: str

    def to_dict(self) -> dict[str, str]:
        """Convert the response object into a JSON-safe dictionary."""
        return {"message": self.message}
