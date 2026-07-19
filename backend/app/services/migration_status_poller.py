"""Migration Status Poller — polls ECS task status and updates migration state.

Runs as a background thread or can be invoked via API endpoint.
Polls ECS DescribeTasks every N seconds and updates:
- ECSTask status
- MigrationJob progress
- WebSocket broadcasts for real-time UI updates
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.extensions import db
from app.models.ecs_task import ECSTask, ECSTaskStatus
from app.models.migration import MigrationJob, MigrationStatus
from app.services.ecs_manager import ECSManager, TaskStatus
from app.services.log_streaming_service import LogStreamingService
from app.services.websocket_service import websocket_service
from app.utils.aws_client import AWSClient

logger = logging.getLogger(__name__)


class MigrationStatusPoller:
    """Polls ECS task status and updates migration state in real-time."""

    POLL_INTERVAL = 5  # seconds
    MAX_POLL_DURATION = 3600  # 1 hour

    def __init__(self, aws_client: AWSClient | None = None) -> None:
        self._aws_client = aws_client or AWSClient()
        self._active_polls: dict[int, threading.Thread] = {}

    def start_polling(self, ecs_task_id: int) -> None:
        """Start a background thread to poll an ECS task until completion."""
        if ecs_task_id in self._active_polls:
            logger.info("Polling already active for task %d", ecs_task_id)
            return

        thread = threading.Thread(
            target=self._poll_loop,
            args=(ecs_task_id,),
            daemon=True,
            name=f"poller-{ecs_task_id}",
        )
        self._active_polls[ecs_task_id] = thread
        thread.start()
        logger.info("Started polling for ECS task %d", ecs_task_id)

    def _poll_loop(self, ecs_task_id: int) -> None:
        """Background polling loop for a single ECS task."""
        try:
            # Wait until the execution thread has populated the task_arn.
            # The prepare_migration() call creates the record with empty ARNs;
            # execute_migration_background() fills them in after RunTask.
            for _ in range(120):  # up to 10 minutes
                task = ECSTask.query.get(ecs_task_id)
                if task and task.task_arn:
                    break
                if task and task.status == ECSTaskStatus.FAILED:
                    logger.info("Task %d failed before polling started", ecs_task_id)
                    return
                import time
                time.sleep(5)
            else:
                logger.error("Timed out waiting for task %d to get a task_arn", ecs_task_id)
                self._fail_task_with_error(ecs_task_id, "Timed out waiting for ECS task to launch.")
                return

            if not task:
                logger.error("ECS task %d not found", ecs_task_id)
                return

            migration = MigrationJob.query.get(task.migration_id)
            if not migration:
                logger.error("Migration %d not found for task %d", task.migration_id, ecs_task_id)
                return

            from app.models.aws_connection import AWSConnection
            aws_connection = AWSConnection.query.get(task.aws_connection_id)
            if not aws_connection:
                logger.error("AWS connection %d not found", task.aws_connection_id)
                return

            # Get AWS clients
            credentials = self._aws_client.assume_role(
                aws_connection.role_arn,
                aws_connection.external_id,
                aws_connection.aws_region,
            )
            ecs_client = self._aws_client.get_boto3_client(
                "ecs", credentials=credentials, region=aws_connection.aws_region
            )
            logs_client = self._aws_client.get_boto3_client(
                "logs", credentials=credentials, region=aws_connection.aws_region
            )

            ecs_manager = ECSManager(ecs_client=ecs_client, region=aws_connection.aws_region)
            log_service = LogStreamingService(logs_client=logs_client, region=aws_connection.aws_region)

            # Poll until terminal state
            last_log_token = None
            last_status_str = ""

            def on_status_change(status: TaskStatus) -> None:
                nonlocal last_status_str
                last_status_str = status.status
                self._update_task_status(task, status)
                self._broadcast_status_update(task, migration, status)

            # Start log streaming in a separate thread once we have a log stream
            log_thread = None

            def _start_log_streaming_when_ready():
                nonlocal log_thread
                for _ in range(60):  # up to 5 minutes
                    db.session.refresh(task)
                    if task.log_stream_name:
                        log_thread = threading.Thread(
                            target=self._stream_logs,
                            args=(log_service, task, migration),
                            daemon=True,
                        )
                        log_thread.start()
                        return
                    import time
                    time.sleep(5)

            log_watcher = threading.Thread(
                target=_start_log_streaming_when_ready,
                daemon=True,
            )
            log_watcher.start()

            # Poll task status
            final_status = ecs_manager.poll_until_terminal(
                cluster_arn=task.cluster_arn,
                task_arn=task.task_arn,
                callback=on_status_change,
                poll_interval=self.POLL_INTERVAL,
                max_wait=self.MAX_POLL_DURATION,
            )

            # Handle terminal state
            self._handle_terminal_state(task, migration, final_status, ecs_manager)

        except Exception as exc:
            logger.exception("Error in polling loop for task %d: %s", ecs_task_id, exc)
            self._fail_task_with_error(ecs_task_id, str(exc))
        finally:
            self._active_polls.pop(ecs_task_id, None)

    def _update_task_status(self, task: ECSTask, status: TaskStatus) -> None:
        """Update ECSTask record with current status."""
        task.status = status.status
        if status.is_stopped:
            task.stopped_at = __import__("datetime").datetime.utcnow()
            task.exit_code = status.exit_code
            task.reason = status.container_reason or status.stopped_reason
        db.session.commit()

    def _broadcast_status_update(
        self,
        task: ECSTask,
        migration: MigrationJob,
        status: TaskStatus,
    ) -> None:
        """Broadcast status update via WebSocket."""
        websocket_service.broadcast_ecs_task_update(
            task.id,
            {
                "status": status.status,
                "task_arn": task.task_arn,
                "exit_code": status.exit_code,
                "stopped_reason": status.stopped_reason,
                "container_reason": status.container_reason,
            },
        )

    def _stream_logs(
        self,
        log_service: LogStreamingService,
        task: ECSTask,
        migration: MigrationJob,
    ) -> None:
        """Stream CloudWatch logs for the task."""
        def on_log_batch(events: list) -> None:
            messages = [e.message for e in events]
            websocket_service.broadcast_migration_update(
                migration.id,
                {
                    "type": "logs",
                    "logs": messages,
                    "task_id": task.id,
                },
            )

        try:
            log_service.stream_logs(
                log_stream_name=task.log_stream_name,
                callback=on_log_batch,
                poll_interval=3,
                max_duration=self.MAX_POLL_DURATION,
            )
        except Exception as exc:
            logger.warning("Log streaming error for task %d: %s", task.id, exc)

    def _handle_terminal_state(
        self,
        task: ECSTask,
        migration: MigrationJob,
        status: TaskStatus,
        ecs_manager: ECSManager,
    ) -> None:
        """Handle the final state of an ECS task."""
        if status.is_failed:
            error_msg = ecs_manager.get_failure_message(status)
            task.status = ECSTaskStatus.FAILED
            task.exit_code = status.exit_code
            task.reason = error_msg
            migration.status = MigrationStatus.FAILED
            migration.error_message = error_msg
            db.session.commit()

            websocket_service.broadcast_ecs_task_update(
                task.id,
                {
                    "status": "FAILED",
                    "error": {
                        "exitCode": status.exit_code,
                        "reason": error_msg,
                        "containerReason": status.container_reason,
                    },
                },
            )
            websocket_service.broadcast_migration_update(
                migration.id,
                {
                    "status": MigrationStatus.FAILED,
                    "error": error_msg,
                },
            )
            logger.error("Migration %d failed: %s", migration.id, error_msg)

        else:
            # Success
            task.status = ECSTaskStatus.SUCCEEDED
            task.exit_code = status.exit_code or 0
            db.session.commit()

            migration.status = MigrationStatus.COMPLETED
            migration.completed_at = __import__("datetime").datetime.utcnow()
            migration.progress_percent = 100.0
            db.session.commit()

            websocket_service.broadcast_ecs_task_update(
                task.id,
                {"status": "SUCCEEDED"},
            )
            websocket_service.broadcast_migration_update(
                migration.id,
                {
                    "status": MigrationStatus.COMPLETED,
                    "message": "Migration completed successfully",
                },
            )
            logger.info("Migration %d completed successfully", migration.id)

    def _fail_task_with_error(self, ecs_task_id: int, error_msg: str) -> None:
        """Mark a task as failed due to polling error."""
        task = ECSTask.query.get(ecs_task_id)
        if not task:
            return

        task.status = ECSTaskStatus.FAILED
        task.reason = f"Polling error: {error_msg}"
        db.session.commit()

        migration = MigrationJob.query.get(task.migration_id)
        if migration:
            migration.status = MigrationStatus.FAILED
            migration.error_message = error_msg
            db.session.commit()

            websocket_service.broadcast_migration_update(
                migration.id,
                {
                    "status": MigrationStatus.FAILED,
                    "error": error_msg,
                },
            )
