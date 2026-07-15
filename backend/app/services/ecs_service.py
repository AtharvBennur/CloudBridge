"""Service layer for ECS/Fargate task execution."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from botocore.exceptions import ClientError
from flask import current_app

from app.extensions import db
from app.models.aws_connection import AWSConnection
from app.models.ecs_task import ECSTask, ECSTaskStatus
from app.models.migration import MigrationJob
from app.utils.aws_client import AWSClient


class ECSServiceError(Exception):
    """Base exception for ECS service errors."""


class ECSTaskNotFoundError(ECSServiceError):
    """Raised when an ECS task cannot be located."""


class ECSValidationError(ECSServiceError):
    """Raised when ECS configuration is invalid."""


class ECSService:
    """Coordinates ECS/Fargate task execution for migrations."""

    def __init__(self, aws_client: AWSClient | None = None, logger: Any | None = None) -> None:
        self._aws_client = aws_client or AWSClient(logger=logger)
        self._logger = logger

    def create_task(
        self,
        migration_id: int,
        aws_connection_id: int,
        cluster_arn: str,
        task_definition_arn: str,
        launch_type: str = "FARGATE",
        subnet_ids: list[str] | None = None,
        security_group_ids: list[str] | None = None,
        cpu: str = "256",
        memory: str = "512",
    ) -> ECSTask:
        """Create and register an ECS task for migration execution."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise ECSTaskNotFoundError(f"Migration job {migration_id} was not found.")

        aws_connection = AWSConnection.query.get(aws_connection_id)
        if not aws_connection:
            raise ECSTaskNotFoundError(f"AWS connection {aws_connection_id} was not found.")

        task = ECSTask(
            migration_id=migration_id,
            aws_connection_id=aws_connection_id,
            cluster_arn=cluster_arn,
            task_definition_arn=task_definition_arn,
            launch_type=launch_type,
            subnet_ids=json.dumps(subnet_ids) if subnet_ids else None,
            security_group_ids=json.dumps(security_group_ids) if security_group_ids else None,
            cpu=cpu,
            memory=memory,
            status=ECSTaskStatus.PENDING,
        )
        db.session.add(task)
        db.session.commit()

        self._log_info("ECS task created", task.id, migration_id)
        return task

    def start_task(self, task_id: int) -> ECSTask:
        """Start an ECS task using AWS ECS API."""
        task = ECSTask.query.get(task_id)
        if not task:
            raise ECSTaskNotFoundError(f"ECS task {task_id} was not found.")

        aws_connection = AWSConnection.query.get(task.aws_connection_id)
        if not aws_connection:
            raise ECSTaskNotFoundError(f"AWS connection {task.aws_connection_id} was not found.")

        try:
            # Get credentials via AssumeRole
            credentials = self._aws_client.assume_role(
                aws_connection.role_arn,
                aws_connection.external_id,
                aws_connection.aws_region,
            )

            # Parse subnet and security group IDs
            subnet_ids = json.loads(task.subnet_ids) if task.subnet_ids else []
            security_group_ids = json.loads(task.security_group_ids) if task.security_group_ids else []

            # Start ECS task
            ecs_client = self._aws_client.get_boto3_client("ecs", credentials=credentials, region=aws_connection.aws_region)
            response = ecs_client.run_task(
                cluster=task.cluster_arn,
                taskDefinition=task.task_definition_arn,
                launchType=task.launch_type,
                platformVersion=task.platform_version,
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": subnet_ids,
                        "securityGroups": security_group_ids,
                        "assignPublicIp": "ENABLED",
                    }
                } if subnet_ids else None,
            )

            if response["tasks"]:
                task.task_arn = response["tasks"][0]["taskArn"]
                task.status = ECSTaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                db.session.commit()

                self._log_info("ECS task started", task.id, task.task_arn)
            else:
                raise ECSServiceError("Failed to start ECS task: No tasks returned from ECS API.")

        except ClientError as exc:
            task.status = ECSTaskStatus.FAILED
            task.reason = str(exc)
            db.session.commit()
            raise ECSServiceError(f"Failed to start ECS task: {exc}") from exc

        return task

    def stop_task(self, task_id: int, reason: str | None = None) -> ECSTask:
        """Stop a running ECS task."""
        task = ECSTask.query.get(task_id)
        if not task:
            raise ECSTaskNotFoundError(f"ECS task {task_id} was not found.")

        if task.status != ECSTaskStatus.RUNNING:
            raise ECSServiceError(f"Cannot stop task with status {task.status}")

        aws_connection = AWSConnection.query.get(task.aws_connection_id)
        if not aws_connection:
            raise ECSTaskNotFoundError(f"AWS connection {task.aws_connection_id} was not found.")

        try:
            credentials = self._aws_client.assume_role(
                aws_connection.role_arn,
                aws_connection.external_id,
                aws_connection.aws_region,
            )

            ecs_client = self._aws_client.get_boto3_client("ecs", credentials=credentials, region=aws_connection.aws_region)
            ecs_client.stop_task(
                cluster=task.cluster_arn,
                task=task.task_arn,
                reason=reason or "Stopped by CloudBridge",
            )

            task.status = ECSTaskStatus.STOPPED
            task.stopped_at = datetime.utcnow()
            task.stop_reason = reason
            db.session.commit()

            self._log_info("ECS task stopped", task.id, task.task_arn)

        except ClientError as exc:
            raise ECSServiceError(f"Failed to stop ECS task: {exc}") from exc

        return task

    def get_task_status(self, task_id: int) -> dict[str, Any]:
        """Get the current status of an ECS task from AWS."""
        task = ECSTask.query.get(task_id)
        if not task:
            raise ECSTaskNotFoundError(f"ECS task {task_id} was not found.")

        aws_connection = AWSConnection.query.get(task.aws_connection_id)
        if not aws_connection:
            raise ECSTaskNotFoundError(f"AWS connection {task.aws_connection_id} was not found.")

        try:
            credentials = self._aws_client.assume_role(
                aws_connection.role_arn,
                aws_connection.external_id,
                aws_connection.aws_region,
            )

            ecs_client = self._aws_client.get_boto3_client("ecs", credentials=credentials, region=aws_connection.aws_region)
            response = ecs_client.describe_tasks(
                cluster=task.cluster_arn,
                tasks=[task.task_arn],
            )

            if response["tasks"]:
                task_info = response["tasks"][0]
                task.status = task_info.get("lastStatus", ECSTaskStatus.PENDING)
                task.desired_status = task_info.get("desiredStatus")
                
                if task_info.get("stopCode"):
                    task.stop_reason = task_info.get("stoppedReason")
                
                db.session.commit()

                return {
                    "task_arn": task.task_arn,
                    "status": task.status,
                    "desired_status": task.desired_status,
                    "last_status": task_info.get("lastStatus"),
                    "stop_code": task_info.get("stopCode"),
                    "stopped_reason": task_info.get("stoppedReason"),
                    "containers": task_info.get("containers", []),
                }

        except ClientError as exc:
            raise ECSServiceError(f"Failed to get ECS task status: {exc}") from exc

        return {"task_arn": task.task_arn, "status": task.status}

    def get_task_logs(self, task_id: int, tail_lines: int = 100) -> list[str]:
        """Get CloudWatch logs for an ECS task."""
        task = ECSTask.query.get(task_id)
        if not task:
            raise ECSTaskNotFoundError(f"ECS task {task_id} was not found.")

        aws_connection = AWSConnection.query.get(task.aws_connection_id)
        if not aws_connection:
            raise ECSTaskNotFoundError(f"AWS connection {task.aws_connection_id} was not found.")

        try:
            credentials = self._aws_client.assume_role(
                aws_connection.role_arn,
                aws_connection.external_id,
                aws_connection.aws_region,
            )

            logs_client = self._aws_client.get_boto3_client("logs", credentials=credentials, region=aws_connection.aws_region)
            
            # Get log stream name if not set
            if not task.log_stream_name:
                task.log_stream_name = f"ecs/{task.task_definition_arn.split('/')[-1]}/{task.task_arn.split('/')[-1]}"
                db.session.commit()

            response = logs_client.get_log_events(
                logGroupName=task.log_group_name or "/ecs/cloudbridge",
                logStreamName=task.log_stream_name,
                limit=tail_lines,
            )

            return [event["message"] for event in response.get("events", [])]

        except ClientError as exc:
            raise ECSServiceError(f"Failed to get ECS task logs: {exc}") from exc

    def retry_task(self, task_id: int) -> ECSTask:
        """Retry a failed ECS task."""
        task = ECSTask.query.get(task_id)
        if not task:
            raise ECSTaskNotFoundError(f"ECS task {task_id} was not found.")

        if task.retry_count >= task.max_retries:
            raise ECSServiceError(f"Max retries ({task.max_retries}) exceeded for task {task_id}")

        task.retry_count += 1
        task.status = ECSTaskStatus.PENDING
        task.task_arn = None
        task.started_at = None
        task.stopped_at = None
        task.reason = None
        task.stop_reason = None
        db.session.commit()

        return self.start_task(task_id)

    def delete_task(self, task_id: int) -> None:
        """Delete an ECS task record."""
        task = ECSTask.query.get(task_id)
        if not task:
            raise ECSTaskNotFoundError(f"ECS task {task_id} was not found.")

        # Stop task if running
        if task.status == ECSTaskStatus.RUNNING:
            self.stop_task(task_id, "Task being deleted")

        db.session.delete(task)
        db.session.commit()
        self._log_info("ECS task deleted", task_id)

    def _log_info(self, message: str, task_id: int | None = None, detail: str | None = None) -> None:
        """Write a structured log entry."""
        logger = self._logger or current_app.logger
        if task_id is not None and detail is not None:
            logger.info("%s for ECS task %s (%s)", message, task_id, detail)
        elif task_id is not None:
            logger.info("%s for ECS task %s", message, task_id)
        else:
            logger.info(message)
