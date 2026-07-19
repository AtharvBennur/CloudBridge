"""Registers ECS task definitions for CloudBridge migration workers.

Handles:
- Building the task definition container overrides
- Registering or reusing task definitions
- Passing migration context via environment variables
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegisteredTaskDefinition:
    """Result of registering an ECS task definition."""

    task_definition_arn: str
    family: str
    revision: int
    container_image: str
    cpu: str
    memory: str


class TaskDefinitionRegistrationError(Exception):
    """Raised when task definition registration fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class TaskDefinitionService:
    """Registers and manages ECS task definitions for migration workers."""

    TASK_FAMILY = "cloudbridge-migration-worker"
    DEFAULT_CPU = "512"
    DEFAULT_MEMORY = "1024"

    def __init__(self, ecs_client: Any, logs_client: Any, region: str) -> None:
        self._ecs = ecs_client
        self._logs = logs_client
        self._region = region

    def register_or_reuse(
        self,
        migration_id: int,
        aws_connection_id: int,
        source_db_config_id: int | None = None,
        destination_db_config_id: int | None = None,
        cpu: str | None = None,
        memory: str | None = None,
        container_image: str | None = None,
        execution_role_arn: str = "",
        task_role_arn: str = "",
    ) -> RegisteredTaskDefinition:
        """Register a new task definition revision for the migration.

        Each migration gets its own task definition revision with environment
        variables pointing to the specific migration and database configs.
        If a matching task definition already exists (same family + env vars),
        the existing ARN is reused to avoid unnecessary revisions.
        """
        family = self.TASK_FAMILY
        if not container_image:
            raise TaskDefinitionRegistrationError(
                "container_image is required. The worker image must be built and pushed to ECR first."
            )
        image = container_image
        task_cpu = cpu or self.DEFAULT_CPU
        task_memory = memory or self.DEFAULT_MEMORY

        # Build environment variables for the worker container
        env_vars = self._build_env_vars(
            migration_id=migration_id,
            aws_connection_id=aws_connection_id,
            source_db_config_id=source_db_config_id,
            destination_db_config_id=destination_db_config_id,
        )

        # Build log configuration
        log_config = self._ensure_log_group()

        # Check if an existing task definition revision matches
        existing = self._find_matching_revision(family, env_vars, image, task_cpu, task_memory)
        if existing:
            logger.info(
                "Reusing existing task definition %s for migration %d",
                existing.task_definition_arn,
                migration_id,
            )
            return existing

        container_def = {
            "name": "migration-worker",
            "image": image,
            "essential": True,
            "environment": env_vars,
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": log_config["group_name"],
                    "awslogs-region": self._region,
                    "awslogs-stream-prefix": "migration-worker",
                    "awslogs-create-group": "true",
                },
            },
        }

        task_def = {
            "family": family,
            "containerDefinitions": [container_def],
            "requiresCompatibilities": ["FARGATE"],
            "networkMode": "awsvpc",
            "cpu": task_cpu,
            "memory": task_memory,
        }

        # Set IAM roles if provided (required for Fargate)
        if execution_role_arn:
            task_def["executionRoleArn"] = execution_role_arn
        if task_role_arn:
            task_def["taskRoleArn"] = task_role_arn

        try:
            response = self._ecs.register_task_definition(**task_def)
            td = response["taskDefinition"]
            logger.info(
                "Registered task definition %s:%d for migration %d",
                family,
                td["revision"],
                migration_id,
            )
            return RegisteredTaskDefinition(
                task_definition_arn=td["taskDefinitionArn"],
                family=family,
                revision=td["revision"],
                container_image=image,
                cpu=task_cpu,
                memory=task_memory,
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            error_msg = exc.response.get("Error", {}).get("Message", str(exc))
            if error_code == "ClientException" and "executionRoleArn" in error_msg:
                raise TaskDefinitionRegistrationError(
                    f"Missing or invalid executionRoleArn. The ECS execution role must exist and have "
                    f"ecs-tasks.amazonaws.com in its trust policy. Details: {error_msg}"
                ) from exc
            raise TaskDefinitionRegistrationError(
                f"Failed to register task definition. Ensure ecs:RegisterTaskDefinition permission is granted. Details: {error_msg}"
            ) from exc

    def _find_matching_revision(
        self,
        family: str,
        env_vars: list[dict[str, str]],
        image: str,
        cpu: str,
        memory: str,
    ) -> RegisteredTaskDefinition | None:
        """Check if a task definition revision already exists with matching config."""
        try:
            response = self._ecs.list_task_definitions(familyPrefix=family, sort="DESC")
            arns = response.get("taskDefinitionArns", [])
            if not arns:
                return None

            # Check the most recent revision
            latest_arn = arns[0]
            desc = self._ecs.describe_task_definition(taskDefinition=latest_arn)
            td = desc.get("taskDefinition", {})

            # Verify it matches our expected config
            containers = td.get("containerDefinitions", [])
            if not containers:
                return None

            container = containers[0]
            if container.get("image") != image:
                return None
            if td.get("cpu") != cpu or td.get("memory") != memory:
                return None

            # Compare environment variables
            existing_env = {e["name"]: e["value"] for e in container.get("environment", [])}
            new_env = {e["name"]: e["value"] for e in env_vars}
            if existing_env != new_env:
                return None

            return RegisteredTaskDefinition(
                task_definition_arn=td["taskDefinitionArn"],
                family=family,
                revision=td["revision"],
                container_image=image,
                cpu=cpu,
                memory=memory,
            )
        except ClientError:
            return None

    def _build_env_vars(
        self,
        migration_id: int,
        aws_connection_id: int,
        source_db_config_id: int | None = None,
        destination_db_config_id: int | None = None,
    ) -> list[dict[str, str]]:
        """Build environment variables passed to the worker container."""
        env = [
            {"name": "CLOUDBRIDGE_API_URL", "value": ""},  # Set by caller
            {"name": "MIGRATION_ID", "value": str(migration_id)},
            {"name": "AWS_CONNECTION_ID", "value": str(aws_connection_id)},
        ]
        if source_db_config_id is not None:
            env.append({"name": "SOURCE_DB_CONFIG_ID", "value": str(source_db_config_id)})
        if destination_db_config_id is not None:
            env.append({"name": "DESTINATION_DB_CONFIG_ID", "value": str(destination_db_config_id)})
        return env

    def _ensure_log_group(self) -> dict[str, str]:
        """Ensure the CloudWatch log group exists for ECS tasks."""
        group_name = "/aws/ecs/cloudbridge-migration-workers"
        try:
            self._logs.describe_log_groups(logGroupNamePrefix=group_name)
            # Check if exact group exists
            response = self._logs.describe_log_groups(logGroupNamePrefix=group_name)
            groups = response.get("logGroups", [])
            for g in groups:
                if g["logGroupName"] == group_name:
                    return {"group_name": group_name}
        except ClientError:
            pass

        try:
            self._logs.create_log_group(
                logGroupName=group_name,
                tags={"ManagedBy": "CloudBridge"},
            )
            logger.info("Created CloudWatch log group: %s", group_name)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "ResourceAlreadyExistsException":
                logger.warning("Failed to create log group: %s", exc)
            # Fall back to default group name anyway
        return {"group_name": group_name}
