"""Structured error types for ECS migration operations.

Provides typed error responses with stage, service, resource, and retryability
information instead of generic string messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MigrationError:
    """Structured error returned by migration operations."""

    stage: str  # e.g., "ecr_push", "task_definition", "run_task", "resource_discovery"
    aws_service: str  # e.g., "ecr", "ecs", "iam", "ec2", "logs"
    resource: str  # e.g., "cloudbridge-migration-worker", "arn:aws:..."
    error_code: str  # AWS error code or internal code
    message: str  # Human-readable message
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

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

def ecr_repository_error(message: str, repo_name: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="ecr_repository",
        aws_service="ecr",
        resource=repo_name,
        error_code="ECR_REPOSITORY_ERROR",
        message=message,
        retryable=retryable,
    )


def ecr_push_error(message: str, image_uri: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="ecr_push",
        aws_service="ecr",
        resource=image_uri,
        error_code="ECR_PUSH_FAILED",
        message=message,
        retryable=retryable,
    )


def ecr_auth_error(message: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="ecr_auth",
        aws_service="ecr",
        resource="ecr.amazonaws.com",
        error_code="ECR_AUTH_FAILED",
        message=message,
        retryable=retryable,
    )


def ecs_run_task_error(message: str, cluster: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="run_task",
        aws_service="ecs",
        resource=cluster,
        error_code="ECS_RUN_TASK_FAILED",
        message=message,
        retryable=retryable,
    )


def ecs_describe_tasks_error(message: str, task_arn: str, retryable: bool = True) -> MigrationError:
    return MigrationError(
        stage="describe_tasks",
        aws_service="ecs",
        resource=task_arn,
        error_code="ECS_DESCRIBE_FAILED",
        message=message,
        retryable=retryable,
    )


def task_definition_error(message: str, family: str, retryable: bool = False) -> MigrationError:
    return MigrationError(
        stage="task_definition",
        aws_service="ecs",
        resource=family,
        error_code="TASK_DEFINITION_ERROR",
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


def container_error(message: str, exit_code: int | None = None, retryable: bool = False) -> MigrationError:
    return MigrationError(
        stage="container_execution",
        aws_service="ecs",
        resource="migration-worker",
        error_code="CONTAINER_ERROR",
        message=message,
        retryable=retryable,
        details={"exitCode": exit_code} if exit_code is not None else {},
    )
