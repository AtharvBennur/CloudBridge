"""Service layer for ECS/Fargate task execution."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from botocore.exceptions import ClientError
from flask import current_app

from app.extensions import db
from app.exceptions.ecs import ECSServiceError, ECSTaskNotFoundError, ECSValidationError, ECSResourceError, ECSPermissionError
from app.models.aws_connection import AWSConnection
from app.models.database_config import DatabaseConfig
from app.models.ecs_task import ECSTask, ECSTaskStatus
from app.models.migration import MigrationJob, MigrationStatus
from app.services.ecs_resource_discovery import (
    DiscoveredResources,
    ECSResourceDiscoveryError,
    ECSResourceDiscoveryService,
)
from app.services.ecs_task_definition import (
    RegisteredTaskDefinition,
    TaskDefinitionRegistrationError,
    TaskDefinitionService,
)
from app.services.websocket_service import websocket_service
from app.utils.aws_client import AWSClient


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

    def start_all_pending(self, migration_id: int) -> list[ECSTask]:
        """Start all PENDING ECS tasks for a given migration."""
        tasks = ECSTask.query.filter_by(
            migration_id=migration_id,
            status=ECSTaskStatus.PENDING,
        ).order_by(ECSTask.created_at.asc()).all()

        started: list[ECSTask] = []
        errors: list[str] = []

        for task in tasks:
            try:
                result = self.start_task(task.id)
                started.append(result)
            except ECSServiceError as exc:
                errors.append(f"Task {task.id}: {exc.message}")

        if not started and errors:
            raise ECSServiceError(f"Failed to start any tasks: {'; '.join(errors)}")

        return started

    def start_migration(self, migration_id: int, aws_connection_id: int | None = None) -> ECSTask:
        """Fully automated migration launch: discover resources, register task def, create & launch ECS task.

        The user provides migration_id and optionally an aws_connection_id.
        All AWS infrastructure is auto-discovered or created.
        The migration job status is updated to RUNNING.
        """
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise ECSTaskNotFoundError(f"Migration job {migration_id} was not found.")

        if migration.status in {MigrationStatus.RUNNING, MigrationStatus.COMPLETED}:
            raise ECSValidationError(
                f"Migration cannot be started from status '{migration.status}'."
            )

        # Use provided aws_connection_id, or fall back to the migration's linked connection
        effective_connection_id = aws_connection_id or migration.aws_connection_id
        aws_connection = AWSConnection.query.get(effective_connection_id)
        if not aws_connection:
            raise ECSResourceError(
                "No valid AWS connection found. Select an AWS connection or link one to the migration first."
            )

        if not aws_connection.role_arn:
            raise ECSResourceError(
                f"AWS connection {aws_connection.id} has no role ARN. Complete the connection setup first."
            )

        # Step 1: Assume role to get credentials
        try:
            credentials = self._aws_client.assume_role(
                aws_connection.role_arn,
                aws_connection.external_id,
                aws_connection.aws_region,
            )
        except ValueError as exc:
            raise ECSPermissionError(
                f"Cannot assume AWS role. Check that the IAM role exists and the trust policy allows CloudBridge: {exc}"
            ) from exc

        # Step 2: Discover or create ECS resources
        ecs_client = self._aws_client.get_boto3_client("ecs", credentials=credentials, region=aws_connection.aws_region)
        ec2_client = self._aws_client.get_boto3_client("ec2", credentials=credentials, region=aws_connection.aws_region)
        iam_client = self._aws_client.get_boto3_client("iam", credentials=credentials, region=aws_connection.aws_region)
        logs_client = self._aws_client.get_boto3_client("logs", credentials=credentials, region=aws_connection.aws_region)

        try:
            discovery = ECSResourceDiscoveryService(
                ecs_client=ecs_client,
                ec2_client=ec2_client,
                iam_client=iam_client,
                region=aws_connection.aws_region,
            )
            resources = discovery.discover_or_create()
        except ECSResourceDiscoveryError as exc:
            raise ECSResourceError(f"Failed to discover ECS resources: {exc.message}") from exc

        # Step 3: Register task definition (with IAM roles from discovered resources)
        try:
            task_def_service = TaskDefinitionService(
                ecs_client=ecs_client,
                logs_client=logs_client,
                region=aws_connection.aws_region,
            )
            task_def = task_def_service.register_or_reuse(
                migration_id=migration.id,
                aws_connection_id=aws_connection.id,
                source_db_config_id=migration.source_database_config_id,
                destination_db_config_id=migration.destination_database_config_id,
                execution_role_arn=resources.execution_role_arn,
                task_role_arn=resources.task_role_arn,
            )
        except TaskDefinitionRegistrationError as exc:
            raise ECSResourceError(f"Failed to register task definition: {exc.message}") from exc

        # Step 4: Create the ECS task record
        task = ECSTask(
            migration_id=migration.id,
            aws_connection_id=aws_connection.id,
            cluster_arn=resources.cluster_arn,
            task_definition_arn=task_def.task_definition_arn,
            launch_type="FARGATE",
            platform_version="LATEST",
            subnet_ids=json.dumps(resources.subnet_ids),
            security_group_ids=json.dumps([resources.security_group_id]),
            cpu=task_def.cpu,
            memory=task_def.memory,
            status=ECSTaskStatus.PENDING,
            log_group_name="/aws/ecs/cloudbridge-migration-workers",
        )
        db.session.add(task)
        db.session.commit()

        # Step 5: Update migration status
        migration.status = MigrationStatus.RUNNING
        migration.started_at = datetime.utcnow()
        db.session.commit()

        # Step 6: Resolve database credentials for the worker
        env_vars = [
            {"name": "CLOUDBRIDGE_API_URL", "value": current_app.config.get("API_BASE_URL", "")},
            {"name": "MIGRATION_ID", "value": str(migration.id)},
            {"name": "AWS_CONNECTION_ID", "value": str(aws_connection.id)},
            {"name": "AWS_DEFAULT_REGION", "value": aws_connection.aws_region},
        ]

        # Pass source DB credentials
        if migration.source_database_config_id:
            src_config = DatabaseConfig.query.get(migration.source_database_config_id)
            if src_config:
                env_vars.extend([
                    {"name": "SOURCE_DB_HOST", "value": src_config.host},
                    {"name": "SOURCE_DB_PORT", "value": str(src_config.port)},
                    {"name": "SOURCE_DB_USERNAME", "value": src_config.username},
                    {"name": "SOURCE_DB_NAME", "value": src_config.database_name or src_config.name},
                ])
                # If secret_arn is set, pass it for Secrets Manager retrieval
                if src_config.secret_arn:
                    env_vars.append({"name": "SOURCE_DB_SECRET_ARN", "value": src_config.secret_arn})

        # Pass destination DB credentials
        if migration.destination_database_config_id:
            dst_config = DatabaseConfig.query.get(migration.destination_database_config_id)
            if dst_config:
                env_vars.extend([
                    {"name": "DEST_DB_HOST", "value": dst_config.host},
                    {"name": "DEST_DB_PORT", "value": str(dst_config.port)},
                    {"name": "DEST_DB_USERNAME", "value": dst_config.username},
                    {"name": "DEST_DB_NAME", "value": dst_config.database_name or dst_config.name},
                ])
                if dst_config.secret_arn:
                    env_vars.append({"name": "DEST_DB_SECRET_ARN", "value": dst_config.secret_arn})

        # Step 7: Launch the ECS task
        try:
            response = ecs_client.run_task(
                cluster=resources.cluster_arn,
                taskDefinition=task_def.task_definition_arn,
                launchType="FARGATE",
                platformVersion="LATEST",
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": resources.subnet_ids,
                        "securityGroups": [resources.security_group_id],
                        "assignPublicIp": "ENABLED",
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

            if response.get("tasks"):
                task.task_arn = response["tasks"][0]["taskArn"]
                task.status = ECSTaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                db.session.commit()

                websocket_service.broadcast_ecs_task_update(
                    task.id,
                    {
                        "status": "RUNNING",
                        "task_arn": task.task_arn,
                        "cluster": resources.cluster_name,
                        "message": "ECS task launched successfully",
                    },
                )

                self._log_info("Migration ECS task launched", task.id, task.task_arn)
            else:
                failures = response.get("failures", [])
                failure_reason = failures[0].get("reason", "Unknown failure") if failures else "No tasks returned"
                task.status = ECSTaskStatus.FAILED
                task.reason = failure_reason
                migration.status = MigrationStatus.FAILED
                migration.error_message = f"ECS task launch failed: {failure_reason}"
                db.session.commit()
                raise ECSServiceError(f"ECS task launch failed: {failure_reason}")

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            error_msg = exc.response.get("Error", {}).get("Message", str(exc))
            task.status = ECSTaskStatus.FAILED
            task.reason = f"{error_code}: {error_msg}"
            migration.status = MigrationStatus.FAILED
            migration.error_message = f"ECS launch error ({error_code}): {error_msg}"
            db.session.commit()

            if error_code == "AccessDeniedException":
                raise ECSPermissionError(
                    f"AWS IAM permission denied. Ensure the role has ecs:RunTask permission: {error_msg}"
                ) from exc
            raise ECSServiceError(f"Failed to launch ECS task: {error_msg}") from exc

        websocket_service.broadcast_migration_update(
            migration.id,
            {
                "status": MigrationStatus.RUNNING,
                "message": "Migration started on ECS/Fargate",
            },
        )

        return task

    def _log_info(self, message: str, task_id: int | None = None, detail: str | None = None) -> None:
        """Write a structured log entry."""
        logger = self._logger or current_app.logger
        if task_id is not None and detail is not None:
            logger.info("%s for ECS task %s (%s)", message, task_id, detail)
        elif task_id is not None:
            logger.info("%s for ECS task %s", message, task_id)
        else:
            logger.info(message)
