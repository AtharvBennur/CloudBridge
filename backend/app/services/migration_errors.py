"""Structured error types for Lambda migration operations.

Provides typed error responses with stage, service, resource, and retryability
information instead of generic string messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MigrationError(Exception):
    """Structured error returned by migration operations."""

    stage: str  # e.g., "lambda_invocation", "dynamodb_write", "sqs_send", "schema_discovery"
    aws_service: str  # e.g., "lambda", "dynamodb", "sqs", "iam", "ec2", "logs"
    resource: str  # e.g., "cloudbridge-migration-worker", "arn:aws:..."
    error_code: str  # AWS error code or internal code
    message: str  # Human-readable message
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize the Exception with the message."""
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "awsService": self.aws_service,
            "resource": self.resource,
            "errorCode": self.error_code,
            "message": self.message,
            "retryable": self.retryable,
            **self.details,
        }

    def __str__(self) -> str:
        return f"[{self.stage}] {self.aws_service}/{self.resource}: {self.message}"


# ── Factory functions for common errors ────────────────────────────────────

def lambda_invocation_error(message: str, function_name: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="lambda_invocation",
        aws_service="lambda",
        resource=function_name,
        error_code="LAMBDA_INVOCATION_FAILED",
        message=message,
        retryable=retryable,
    )


def dynamodb_write_error(message: str, table_name: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="dynamodb_write",
        aws_service="dynamodb",
        resource=table_name,
        error_code="DYNAMODB_WRITE_FAILED",
        message=message,
        retryable=retryable,
    )


def sqs_send_error(message: str, queue_url: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="sqs_send",
        aws_service="sqs",
        resource=queue_url,
        error_code="SQS_SEND_FAILED",
        message=message,
        retryable=retryable,
    )


def iam_role_error(message: str, role_name: str, retryable: bool = False) -> MigrationError:
    return MigrationError(
        stage="iam_role",
        aws_service="iam",
        resource=role_name,
        error_code="IAM_ROLE_ERROR",
        message=message,
        retryable=retryable,
    )


def resource_discovery_error(message: str, resource_type: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="resource_discovery",
        aws_service="ec2",
        resource=resource_type,
        error_code="RESOURCE_DISCOVERY_FAILED",
        message=message,
        retryable=retryable,
    )


def log_stream_error(message: str, log_group: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="log_stream",
        aws_service="logs",
        resource=log_group,
        error_code="LOG_STREAM_ERROR",
        message=message,
        retryable=retryable,
    )


def lambda_function_error(message: str, function_name: str, retryable: bool = False) -> MigrationError:
    return MigrationError(
        stage="lambda_execution",
        aws_service="lambda",
        resource=function_name,
        error_code="LAMBDA_FUNCTION_ERROR",
        message=message,
        retryable=retryable,
    )


def schema_discovery_error(message: str, database_name: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="schema_discovery",
        aws_service="lambda",
        resource=database_name,
        error_code="SCHEMA_DISCOVERY_FAILED",
        message=message,
        retryable=retryable,
    )
