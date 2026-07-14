"""Request and response schemas for ECS endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.models.ecs_task import ECSTask


@dataclass(frozen=True)
class CreateECSTaskRequest:
    """Represents the payload required to create an ECS task."""

    migration_id: int
    aws_connection_id: int
    cluster_arn: str
    task_definition_arn: str
    launch_type: str = "FARGATE"
    subnet_ids: list[str] | None = None
    security_group_ids: list[str] | None = None
    cpu: str = "256"
    memory: str = "512"

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "CreateECSTaskRequest":
        """Convert raw JSON into a validated creation request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        migration_id = payload.get("migration_id")
        aws_connection_id = payload.get("aws_connection_id")
        cluster_arn = payload.get("cluster_arn")
        task_definition_arn = payload.get("task_definition_arn")
        launch_type = payload.get("launch_type", "FARGATE")
        subnet_ids = payload.get("subnet_ids")
        security_group_ids = payload.get("security_group_ids")
        cpu = payload.get("cpu", "256")
        memory = payload.get("memory", "512")

        if not migration_id or not aws_connection_id or not cluster_arn or not task_definition_arn:
            raise ValueError("migration_id, aws_connection_id, cluster_arn, and task_definition_arn are required.")

        try:
            migration_id = int(migration_id)
            aws_connection_id = int(aws_connection_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("migration_id and aws_connection_id must be integers.") from exc

        if launch_type not in {"FARGATE", "EC2"}:
            raise ValueError("launch_type must be either FARGATE or EC2.")

        if not isinstance(cluster_arn, str) or not cluster_arn.strip():
            raise ValueError("cluster_arn must be a non-empty string.")
        if not isinstance(task_definition_arn, str) or not task_definition_arn.strip():
            raise ValueError("task_definition_arn must be a non-empty string.")

        return cls(
            migration_id=migration_id,
            aws_connection_id=aws_connection_id,
            cluster_arn=cluster_arn.strip(),
            task_definition_arn=task_definition_arn.strip(),
            launch_type=launch_type,
            subnet_ids=subnet_ids if isinstance(subnet_ids, list) else None,
            security_group_ids=security_group_ids if isinstance(security_group_ids, list) else None,
            cpu=str(cpu),
            memory=str(memory),
        )


@dataclass(frozen=True)
class ECSTaskResponse:
    """Represents the structured JSON returned by ECS endpoints."""

    id: int
    migration_id: int
    aws_connection_id: int | None
    task_arn: str | None
    task_definition_arn: str | None
    cluster_arn: str | None
    launch_type: str
    platform_version: str | None
    subnet_ids: list[str] | None
    security_group_ids: list[str] | None
    status: str
    desired_status: str | None
    cpu: str
    memory: str
    started_at: str | None
    stopped_at: str | None
    exit_code: int | None
    reason: str | None
    stop_reason: str | None
    retry_count: int
    max_retries: int
    log_group_name: str | None
    log_stream_name: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        return {
            "id": self.id,
            "migration_id": self.migration_id,
            "aws_connection_id": self.aws_connection_id,
            "task_arn": self.task_arn,
            "task_definition_arn": self.task_definition_arn,
            "cluster_arn": self.cluster_arn,
            "launch_type": self.launch_type,
            "platform_version": self.platform_version,
            "subnet_ids": self.subnet_ids,
            "security_group_ids": self.security_group_ids,
            "status": self.status,
            "desired_status": self.desired_status,
            "cpu": self.cpu,
            "memory": self.memory,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "exit_code": self.exit_code,
            "reason": self.reason,
            "stop_reason": self.stop_reason,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "log_group_name": self.log_group_name,
            "log_stream_name": self.log_stream_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_model(cls, task: ECSTask) -> "ECSTaskResponse":
        """Build a response DTO from a persisted ECS task."""
        return cls(
            id=task.id,
            migration_id=task.migration_id,
            aws_connection_id=task.aws_connection_id,
            task_arn=task.task_arn,
            task_definition_arn=task.task_definition_arn,
            cluster_arn=task.cluster_arn,
            launch_type=task.launch_type,
            platform_version=task.platform_version,
            subnet_ids=json.loads(task.subnet_ids) if task.subnet_ids else None,
            security_group_ids=json.loads(task.security_group_ids) if task.security_group_ids else None,
            status=task.status,
            desired_status=task.desired_status,
            cpu=task.cpu,
            memory=task.memory,
            started_at=task.started_at.isoformat() if task.started_at else None,
            stopped_at=task.stopped_at.isoformat() if task.stopped_at else None,
            exit_code=task.exit_code,
            reason=task.reason,
            stop_reason=task.stop_reason,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            log_group_name=task.log_group_name,
            log_stream_name=task.log_stream_name,
            created_at=task.created_at.isoformat() if task.created_at else "",
            updated_at=task.updated_at.isoformat() if task.updated_at else "",
        )
