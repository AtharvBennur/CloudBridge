"""ECS Manager — handles ECS task lifecycle, polling, and status updates.

Handles:
- Running ECS tasks (RunTask)
- Describing task status (DescribeTasks)
- Stopping tasks
- Polling task status with exponential backoff
- Extracting container exit codes and failure reasons
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from botocore.exceptions import ClientError

from app.services.migration_errors import (
    MigrationError,
    container_error,
    ecs_describe_tasks_error,
    ecs_run_task_error,
)

logger = logging.getLogger(__name__)


@dataclass
class TaskStatus:
    """Current status of an ECS task."""

    task_arn: str
    status: str  # PROVISIONING, PENDING, RUNNING, STOPPED
    desired_status: str = ""
    stopped_reason: str = ""
    stop_code: str = ""
    exit_code: int | None = None
    container_reason: str = ""
    containers: list[dict[str, Any]] = field(default_factory=list)
    started_at: str = ""
    stopped_at: str = ""

    @property
    def is_running(self) -> bool:
        return self.status == "RUNNING"

    @property
    def is_stopped(self) -> bool:
        return self.status == "STOPPED"

    @property
    def is_failed(self) -> bool:
        if not self.is_stopped:
            return False
        return self.exit_code not in (None, 0) or bool(self.container_reason)


class ECSManager:
    """Manages ECS task execution and status polling."""

    def __init__(self, ecs_client: Any, region: str) -> None:
        self._ecs = ecs_client
        self._region = region

    def run_task(
        self,
        cluster_arn: str,
        task_definition_arn: str,
        subnet_ids: list[str],
        security_group_ids: list[str],
        env_vars: list[dict[str, str]],
        launch_type: str = "FARGATE",
        platform_version: str = "LATEST",
        assign_public_ip: str = "ENABLED",
    ) -> dict[str, Any]:
        """Launch an ECS task. Returns the raw RunTask response.

        Raises MigrationError on failure.
        """
        try:
            response = self._ecs.run_task(
                cluster=cluster_arn,
                taskDefinition=task_definition_arn,
                launchType=launch_type,
                platformVersion=platform_version,
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": subnet_ids,
                        "securityGroups": security_group_ids,
                        "assignPublicIp": assign_public_ip,
                    }
                },
                overrides={
                    "containerOverrides": [
                        {
                            "name": "migration-worker",
                            "environment": env_vars,
                        }
                    ]
                },
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            error_msg = exc.response.get("Error", {}).get("Message", str(exc))
            retryable = error_code in (
                "ThrottlingException",
                "TooManyRequestsException",
                "ServiceUnavailableException",
            )
            raise ecs_run_task_error(
                f"{error_code}: {error_msg}",
                cluster_arn,
                retryable=retryable,
            ) from exc

        # Check for failures
        failures = response.get("failures", [])
        if failures:
            failure = failures[0]
            reason = failure.get("reason", "Unknown")
            detail = failure.get("detail", "")
            raise ecs_run_task_error(
                f"RunTask failed: {reason} — {detail}",
                cluster_arn,
                retryable="RESOURCE" not in reason.upper(),
            )

        tasks = response.get("tasks", [])
        if not tasks:
            raise ecs_run_task_error(
                "RunTask returned no tasks and no failures",
                cluster_arn,
                retryable=True,
            )

        return tasks[0]

    def describe_task(self, cluster_arn: str, task_arn: str) -> TaskStatus:
        """Describe an ECS task and return its current status."""
        try:
            response = self._ecs.describe_tasks(
                cluster=cluster_arn,
                tasks=[task_arn],
            )
        except ClientError as exc:
            raise ecs_describe_tasks_error(
                f"DescribeTasks failed: {exc}",
                task_arn,
                retryable=True,
            ) from exc

        tasks = response.get("tasks", [])
        if not tasks:
            # Task may have been cleaned up
            return TaskStatus(
                task_arn=task_arn,
                status="STOPPED",
                stopped_reason="Task not found (may have been cleaned up)",
            )

        task = tasks[0]
        last_status = task.get("lastStatus", "UNKNOWN")
        containers = task.get("containers", [])

        exit_code = None
        container_reason = ""
        if containers:
            container = containers[0]
            exit_code = container.get("exitCode")
            container_reason = container.get("reason", "")

        return TaskStatus(
            task_arn=task_arn,
            status=last_status,
            desired_status=task.get("desiredStatus", ""),
            stopped_reason=task.get("stoppedReason", ""),
            stop_code=task.get("stopCode", ""),
            exit_code=exit_code,
            container_reason=container_reason,
            containers=containers,
            started_at=task.get("startedAt", ""),
            stopped_at=task.get("stoppedAt", ""),
        )

    def stop_task(self, cluster_arn: str, task_arn: str, reason: str = "Stopped by CloudBridge") -> None:
        """Stop a running ECS task."""
        try:
            self._ecs.stop_task(
                cluster=cluster_arn,
                task=task_arn,
                reason=reason,
            )
            logger.info("Stopped ECS task: %s", task_arn)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code == "TaskNotFoundException":
                logger.info("Task already stopped or not found: %s", task_arn)
                return
            raise ecs_run_task_error(
                f"Failed to stop task: {exc}",
                cluster_arn,
                retryable=True,
            ) from exc

    def poll_until_terminal(
        self,
        cluster_arn: str,
        task_arn: str,
        callback: Any = None,
        poll_interval: int = 5,
        max_wait: int = 3600,
    ) -> TaskStatus:
        """Poll task status until it reaches a terminal state (STOPPED).

        Args:
            cluster_arn: ECS cluster ARN
            task_arn: Task ARN to poll
            callback: Optional callable(status: TaskStatus) invoked on each poll
            poll_interval: Seconds between polls
            max_wait: Maximum seconds to wait before timing out

        Returns:
            Final TaskStatus when task reaches STOPPED
        """
        deadline = time.time() + max_wait
        last_status = ""

        while time.time() < deadline:
            status = self.describe_task(cluster_arn, task_arn)

            if callback and status.status != last_status:
                callback(status)
                last_status = status.status

            if status.is_stopped:
                logger.info(
                    "Task %s reached terminal state: %s (exit=%s, reason=%s)",
                    task_arn,
                    status.status,
                    status.exit_code,
                    status.container_reason or status.stopped_reason,
                )
                return status

            logger.debug("Task %s status: %s", task_arn, status.status)
            time.sleep(poll_interval)

        raise ecs_run_task_error(
            f"Task {task_arn} did not reach terminal state within {max_wait}s",
            cluster_arn,
            retryable=False,
        )

    def get_failure_message(self, status: TaskStatus) -> str:
        """Extract a human-readable failure message from a stopped task."""
        if status.container_reason:
            return f"Container error: {status.container_reason}"
        if status.stopped_reason:
            return f"Task stopped: {status.stopped_reason}"
        if status.exit_code is not None and status.exit_code != 0:
            return f"Container exited with code {status.exit_code}"
        return "Task stopped without a clear reason"
