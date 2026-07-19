"""Migration Execution Service — orchestrates the full migration lifecycle.

Flow:
  Start Migration
    ↓
  Discover AWS Resources (cluster, VPC, subnets, SG, IAM roles)
    ↓
  Build Worker Image & Push to ECR
    ↓
  Register Task Definition (with ECR image URI)
    ↓
  Run ECS Task
    ↓
  Stream CloudWatch Logs
    ↓
  Poll ECS Task Status
    ↓
  Update Progress
    ↓
  Migration Completed/Failed
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any

from flask import current_app

from app.extensions import db
from app.exceptions.ecs import (
    ECSPermissionError,
    ECSResourceError,
    ECSServiceError,
    ECSTaskNotFoundError,
    ECSValidationError,
)
from app.models.aws_connection import AWSConnection
from app.models.database_config import DatabaseConfig
from app.models.ecs_task import ECSTask, ECSTaskStatus
from app.models.migration import MigrationJob, MigrationStatus
from app.services.ecr_manager import ECRManager
from app.services.ecs_manager import ECSManager, TaskStatus
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
from app.services.log_streaming_service import LogStreamingService
from app.services.migration_errors import MigrationError
from app.services.websocket_service import websocket_service
from app.utils.aws_client import AWSClient

logger = logging.getLogger(__name__)

# Path to the worker directory (relative to project root)
WORKER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "worker")


class MigrationExecutionService:
    """Orchestrates the complete migration execution lifecycle."""

    def __init__(self, aws_client: AWSClient | None = None) -> None:
        self._aws_client = aws_client or AWSClient()

    # ------------------------------------------------------------------
    # Phase 1: Synchronous validation & task-record creation (fast).
    # ------------------------------------------------------------------
    def prepare_migration(
        self,
        migration_id: int,
        aws_connection_id: int | None = None,
    ) -> ECSTask:
        """Validate inputs, reset state, and create a PENDING task record.

        Returns the ECSTask record quickly so the HTTP request can return 202.
        Raises ECSValidationError / ECSTaskNotFoundError / ECSResourceError on
        validation failures.
        """
        # ── Validate migration ──────────────────────────────────────────────
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise ECSTaskNotFoundError(f"Migration job {migration_id} was not found.")

        if migration.status in {MigrationStatus.RUNNING, MigrationStatus.COMPLETED}:
            raise ECSValidationError(
                f"Migration cannot be started from status '{migration.status}'."
            )

        # ── Reset migration state for fresh execution ───────────────────────
        self._reset_migration_state(migration)

        # ── Validate database configs have database_name ────────────────────
        if migration.source_database_config_id:
            src = DatabaseConfig.query.get(migration.source_database_config_id)
            if src and not src.database_name:
                raise ECSValidationError(
                    f"Source database config '{src.name}' (ID {src.id}) has no database_name set. "
                    "Edit the database config and provide the actual database name on the server."
                )
        if migration.destination_database_config_id:
            dst = DatabaseConfig.query.get(migration.destination_database_config_id)
            if dst and not dst.database_name:
                raise ECSValidationError(
                    f"Destination database config '{dst.name}' (ID {dst.id}) has no database_name set. "
                    "Edit the database config and provide the actual database name on the server."
                )

        # ── Resolve AWS connection ──────────────────────────────────────────
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

        # ── Create placeholder ECS task record ─────────────────────────────
        task = ECSTask(
            migration_id=migration.id,
            aws_connection_id=aws_connection.id,
            cluster_arn="",  # filled during execution
            task_definition_arn="",  # filled during execution
            launch_type="FARGATE",
            platform_version="LATEST",
            subnet_ids="[]",
            security_group_ids="[]",
            cpu="1024",
            memory="2048",
            status=ECSTaskStatus.PENDING,
            log_group_name="/aws/ecs/cloudbridge-migration-workers",
        )
        db.session.add(task)

        # ── Mark migration as running ───────────────────────────────────────
        migration.status = MigrationStatus.RUNNING
        migration.started_at = datetime.utcnow()
        db.session.commit()

        websocket_service.broadcast_migration_update(
            migration.id,
            {
                "status": MigrationStatus.RUNNING,
                "message": "Migration preparing…",
            },
        )

        return task

    # ------------------------------------------------------------------
    # Phase 2: Heavy AWS work (runs in a background thread).
    # ------------------------------------------------------------------
    def execute_migration_background(
        self,
        app,
        task_id: int,
        migration_id: int,
        aws_connection_id: int,
    ) -> None:
        """Run the full migration flow in a background thread.

        Must be called inside a new ``threading.Thread`` with ``app`` passed
        explicitly so we can push an application context.
        """
        with app.app_context():
            try:
                self._do_execute(task_id, migration_id, aws_connection_id)
            except Exception as exc:
                logger.exception("Background migration execution failed: %s", exc)
                # Mark task and migration as failed
                task = db.session.get(ECSTask, task_id)
                migration = db.session.get(MigrationJob, migration_id)
                if task:
                    task.status = ECSTaskStatus.FAILED
                    task.reason = str(exc)
                if migration:
                    migration.status = MigrationStatus.FAILED
                    migration.error_message = str(exc)
                db.session.commit()
                websocket_service.broadcast_ecs_task_update(
                    task_id,
                    {"status": "FAILED", "error": str(exc)},
                )
                websocket_service.broadcast_migration_update(
                    migration_id,
                    {"status": MigrationStatus.FAILED, "error": str(exc)},
                )

    # ------------------------------------------------------------------
    # Internal execution logic (called from background thread).
    # ------------------------------------------------------------------
    def _do_execute(
        self,
        task_id: int,
        migration_id: int,
        aws_connection_id: int,
    ) -> None:
        task = db.session.get(ECSTask, task_id)
        migration = db.session.get(MigrationJob, migration_id)
        aws_connection = db.session.get(AWSConnection, aws_connection_id)

        if not task or not migration or not aws_connection:
            raise ECSTaskNotFoundError("Task, migration, or AWS connection not found.")

        # ── Assume role ────────────────────────────────────────────────────
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

        # ── Initialize AWS clients ──────────────────────────────────────────
        ecs_client = self._aws_client.get_boto3_client("ecs", credentials=credentials, region=aws_connection.aws_region)
        ec2_client = self._aws_client.get_boto3_client("ec2", credentials=credentials, region=aws_connection.aws_region)
        iam_client = self._aws_client.get_boto3_client("iam", credentials=credentials, region=aws_connection.aws_region)
        logs_client = self._aws_client.get_boto3_client("logs", credentials=credentials, region=aws_connection.aws_region)
        ecr_client = self._aws_client.get_boto3_client("ecr", credentials=credentials, region=aws_connection.aws_region)

        region = aws_connection.aws_region

        # ── Step 1: Discover or create resources ────────────────────────────
        try:
            discovery = ECSResourceDiscoveryService(
                ecs_client=ecs_client,
                ec2_client=ec2_client,
                iam_client=iam_client,
                region=region,
            )
            resources = discovery.discover_or_create()
        except ECSResourceDiscoveryError as exc:
            raise ECSResourceError(f"Failed to discover ECS resources: {exc.message}") from exc

        # Update task with discovered resource ARNs
        task.cluster_arn = resources.cluster_arn
        task.subnet_ids = json.dumps(resources.subnet_ids)
        task.security_group_ids = json.dumps([resources.security_group_id])

        # ── Step 2: Build and push worker image to ECR ──────────────────────
        ecr_manager = ECRManager(
            ecr_client=ecr_client,
            account_id=aws_connection.aws_account_id,
            region=region,
        )
        pushed_image = ecr_manager.build_and_push(WORKER_DIR)
        logger.info("Worker image pushed: %s", pushed_image.image_uri)

        websocket_service.broadcast_ecs_task_update(
            task.id,
            {"status": "BUILDING", "message": "Worker image pushed to ECR"},
        )

        # ── Step 3: Register task definition with ECR image ─────────────────
        try:
            task_def_service = TaskDefinitionService(
                ecs_client=ecs_client,
                logs_client=logs_client,
                region=region,
            )
            task_def = task_def_service.register_or_reuse(
                migration_id=migration.id,
                aws_connection_id=aws_connection.id,
                source_db_config_id=migration.source_database_config_id,
                destination_db_config_id=migration.destination_database_config_id,
                execution_role_arn=resources.execution_role_arn,
                task_role_arn=resources.task_role_arn,
                container_image=pushed_image.image_uri,
            )
        except TaskDefinitionRegistrationError as exc:
            raise ECSResourceError(f"Failed to register task definition: {exc.message}") from exc

        task.task_definition_arn = task_def.task_definition_arn
        task.cpu = task_def.cpu
        task.memory = task_def.memory
        db.session.commit()

        # ── Step 4: Build environment variables ─────────────────────────────
        env_vars = self._build_env_vars(migration, aws_connection)

        # ── Step 5: Launch ECS task ─────────────────────────────────────────
        ecs_manager = ECSManager(ecs_client=ecs_client, region=region)

        try:
            task_info = ecs_manager.run_task(
                cluster_arn=resources.cluster_arn,
                task_definition_arn=task_def.task_definition_arn,
                subnet_ids=resources.subnet_ids,
                security_group_ids=[resources.security_group_id],
                env_vars=env_vars,
            )
        except MigrationError as exc:
            self._fail_migration(migration, task, exc)
            raise ECSResourceError(exc.message) from exc

        # ── Step 6: Update task with ARN ───────────────────────────────────
        task.task_arn = task_info["taskArn"]
        task.status = ECSTaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        db.session.commit()

        # ── Step 7: Discover log stream ────────────────────────────────────
        log_service = LogStreamingService(logs_client=logs_client, region=region)
        task_def_family = task_def.family
        log_stream = log_service.find_log_stream(task.task_arn, task_def_family)
        if log_stream:
            task.log_stream_name = log_stream
            db.session.commit()

        # ── Step 8: Broadcast success ──────────────────────────────────────
        websocket_service.broadcast_ecs_task_update(
            task.id,
            {
                "status": "RUNNING",
                "task_arn": task.task_arn,
                "cluster": resources.cluster_name,
                "image": pushed_image.image_uri,
                "message": "ECS task launched successfully",
            },
        )
        websocket_service.broadcast_migration_update(
            migration.id,
            {
                "status": MigrationStatus.RUNNING,
                "message": "Migration started on ECS/Fargate",
            },
        )

        logger.info("Migration ECS task launched: task=%s, image=%s", task.task_arn, pushed_image.image_uri)

    def _reset_migration_state(self, migration: MigrationJob) -> None:
        """Reset migration progress fields for a fresh execution."""
        migration.progress_percent = 0.0
        migration.rows_migrated = 0
        migration.current_table = None
        migration.error_message = None
        migration.retry_count = 0
        db.session.commit()
        logger.info("Reset migration state for job %d", migration.id)

    def _build_env_vars(
        self,
        migration: MigrationJob,
        aws_connection: AWSConnection,
    ) -> list[dict[str, str]]:
        """Build environment variables for the worker container."""
        env_vars = [
            {"name": "CLOUDBRIDGE_API_URL", "value": current_app.config.get("API_BASE_URL", "")},
            {"name": "MIGRATION_ID", "value": str(migration.id)},
            {"name": "AWS_CONNECTION_ID", "value": str(aws_connection.id)},
            {"name": "AWS_DEFAULT_REGION", "value": aws_connection.aws_region},
        ]

        if migration.source_database_config_id:
            src = DatabaseConfig.query.get(migration.source_database_config_id)
            if src:
                env_vars.extend([
                    {"name": "SOURCE_DB_HOST", "value": src.host},
                    {"name": "SOURCE_DB_PORT", "value": str(src.port)},
                    {"name": "SOURCE_DB_USERNAME", "value": src.username},
                    {"name": "SOURCE_DB_NAME", "value": src.database_name or src.name},
                ])
                if src.secret_arn:
                    env_vars.append({"name": "SOURCE_DB_SECRET_ARN", "value": src.secret_arn})

        if migration.destination_database_config_id:
            dst = DatabaseConfig.query.get(migration.destination_database_config_id)
            if dst:
                env_vars.extend([
                    {"name": "DEST_DB_HOST", "value": dst.host},
                    {"name": "DEST_DB_PORT", "value": str(dst.port)},
                    {"name": "DEST_DB_USERNAME", "value": dst.username},
                    {"name": "DEST_DB_NAME", "value": dst.database_name or dst.name},
                ])
                if dst.secret_arn:
                    env_vars.append({"name": "DEST_DB_SECRET_ARN", "value": dst.secret_arn})

        return env_vars

    def _fail_migration(
        self,
        migration: MigrationJob,
        task: ECSTask,
        error: MigrationError,
    ) -> None:
        """Mark migration and task as failed with structured error."""
        task.status = ECSTaskStatus.FAILED
        task.reason = str(error)
        migration.status = MigrationStatus.FAILED
        migration.error_message = error.message
        db.session.commit()

        websocket_service.broadcast_ecs_task_update(
            task.id,
            {
                "status": "FAILED",
                "error": error.to_dict(),
            },
        )
