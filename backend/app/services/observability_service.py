"""Service layer for observability, CloudWatch integration, and audit logging."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from botocore.exceptions import ClientError
from flask import current_app, request

from app.extensions import db
from app.models.audit_log import AuditLog, AuditEventType
from app.models.aws_connection import AWSConnection
from app.utils.aws_client import AWSClient


class ObservabilityServiceError(Exception):
    """Base exception for observability service errors."""


class ObservabilityService:
    """Coordinates CloudWatch logging, metrics, and audit logging."""

    def __init__(self, aws_client: AWSClient | None = None, logger: Any | None = None) -> None:
        self._aws_client = aws_client or AWSClient(logger=logger)
        self._logger = logger

    def log_audit_event(
        self,
        event_type: str,
        event_category: str,
        event_description: str,
        migration_id: int | None = None,
        aws_connection_id: int | None = None,
        database_config_id: int | None = None,
        ecs_task_id: int | None = None,
        user_id: str | None = None,
        user_email: str | None = None,
        event_metadata: dict[str, Any] | None = None,
        severity: str = "INFO",
    ) -> AuditLog:
        """Log an audit event to the database."""
        audit_log = AuditLog(
            event_type=event_type,
            event_category=event_category,
            event_description=event_description,
            migration_id=migration_id,
            aws_connection_id=aws_connection_id,
            database_config_id=database_config_id,
            ecs_task_id=ecs_task_id,
            user_id=user_id,
            user_email=user_email,
            event_metadata=json.dumps(event_metadata) if event_metadata else None,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
            severity=severity,
        )
        db.session.add(audit_log)
        db.session.commit()

        self._log_info(f"Audit event logged: {event_type}")
        return audit_log

    def send_cloudwatch_metric(
        self,
        aws_connection_id: int,
        metric_name: str,
        metric_value: float,
        metric_namespace: str = "CloudBridge",
        dimensions: list[dict[str, str]] | None = None,
        unit: str = "Count",
    ) -> None:
        """Send a custom metric to CloudWatch."""
        aws_connection = AWSConnection.query.get(aws_connection_id)
        if not aws_connection:
            raise ObservabilityServiceError(f"AWS connection {aws_connection_id} was not found.")

        try:
            credentials = self._aws_client.assume_role(
                aws_connection.role_arn,
                aws_connection.external_id,
                aws_connection.aws_region,
            )

            cloudwatch_client = self._aws_client.get_boto3_client("cloudwatch", credentials, aws_connection.aws_region)
            
            cloudwatch_client.put_metric_data(
                Namespace=metric_namespace,
                MetricData=[
                    {
                        "MetricName": metric_name,
                        "Value": metric_value,
                        "Unit": unit,
                        "Dimensions": dimensions or [],
                        "Timestamp": datetime.utcnow(),
                    }
                ],
            )

            self._log_info(f"CloudWatch metric sent: {metric_name} = {metric_value}")

        except ClientError as exc:
            self._logger.error(f"Failed to send CloudWatch metric: {exc}")
            raise ObservabilityServiceError(f"Failed to send CloudWatch metric: {exc}") from exc

    def send_cloudwatch_log(
        self,
        aws_connection_id: int,
        log_group_name: str,
        log_stream_name: str,
        message: str,
        log_level: str = "INFO",
    ) -> None:
        """Send a log entry to CloudWatch Logs."""
        aws_connection = AWSConnection.query.get(aws_connection_id)
        if not aws_connection:
            raise ObservabilityServiceError(f"AWS connection {aws_connection_id} was not found.")

        try:
            credentials = self._aws_client.assume_role(
                aws_connection.role_arn,
                aws_connection.external_id,
                aws_connection.aws_region,
            )

            logs_client = self._aws_client.get_boto3_client("logs", credentials, aws_connection.aws_region)
            
            # Create log group if it doesn't exist
            try:
                logs_client.create_log_group(logGroupName=log_group_name)
            except logs_client.exceptions.ResourceAlreadyExistsException:
                pass

            # Create log stream if it doesn't exist
            try:
                logs_client.create_log_stream(
                    logGroupName=log_group_name,
                    logStreamName=log_stream_name,
                )
            except logs_client.exceptions.ResourceAlreadyExistsException:
                pass

            # Send log event
            timestamp = int(datetime.utcnow().timestamp() * 1000)
            logs_client.put_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                logEvents=[
                    {
                        "timestamp": timestamp,
                        "message": f"[{log_level}] {message}",
                    }
                ],
            )

            self._log_info(f"CloudWatch log sent to {log_group_name}/{log_stream_name}")

        except ClientError as exc:
            self._logger.error(f"Failed to send CloudWatch log: {exc}")
            raise ObservabilityServiceError(f"Failed to send CloudWatch log: {exc}") from exc

    def get_migration_metrics(self, migration_id: int) -> dict[str, Any]:
        """Get aggregated metrics for a migration."""
        from app.models.migration import MigrationJob
        from app.models.cdc_event import CDCEvent
        from app.models.ecs_task import ECSTask

        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise ObservabilityServiceError(f"Migration {migration_id} was not found.")

        # Get audit logs for this migration
        audit_logs = AuditLog.query.filter_by(migration_id=migration_id).order_by(AuditLog.occurred_at.desc()).limit(100).all()
        
        # Get CDC event statistics
        cdc_events_total = CDCEvent.query.filter_by(migration_id=migration_id).count()
        cdc_events_processed = CDCEvent.query.filter_by(migration_id=migration_id, status="PROCESSED").count()
        cdc_events_failed = CDCEvent.query.filter_by(migration_id=migration_id, status="FAILED").count()
        
        # Get ECS task information
        ecs_tasks = ECSTask.query.filter_by(migration_id=migration_id).all()

        return {
            "migration_id": migration_id,
            "migration_status": migration.status,
            "progress_percent": migration.progress_percent,
            "rows_migrated": migration.rows_migrated,
            "total_rows": migration.total_rows,
            "retry_count": migration.retry_count,
            "audit_log_count": len(audit_logs),
            "recent_audit_logs": [
                {
                    "event_type": log.event_type,
                    "event_category": log.event_category,
                    "description": log.event_description,
                    "severity": log.severity,
                    "occurred_at": log.occurred_at.isoformat(),
                }
                for log in audit_logs[:10]
            ],
            "cdc_events": {
                "total": cdc_events_total,
                "processed": cdc_events_processed,
                "failed": cdc_events_failed,
                "pending": cdc_events_total - cdc_events_processed - cdc_events_failed,
            },
            "ecs_tasks": [
                {
                    "task_id": task.id,
                    "status": task.status,
                    "task_arn": task.task_arn,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "stopped_at": task.stopped_at.isoformat() if task.stopped_at else None,
                }
                for task in ecs_tasks
            ],
        }

    def get_system_health_metrics(self) -> dict[str, Any]:
        """Get overall system health metrics."""
        from app.models.migration import MigrationJob
        from app.models.aws_connection import AWSConnection
        from app.models.database_config import DatabaseConfig

        total_migrations = MigrationJob.query.count()
        running_migrations = MigrationJob.query.filter_by(status="RUNNING").count()
        failed_migrations = MigrationJob.query.filter_by(status="FAILED").count()
        completed_migrations = MigrationJob.query.filter_by(status="COMPLETED").count()

        total_aws_connections = AWSConnection.query.count()
        active_aws_connections = AWSConnection.query.filter_by(connection_status="CONNECTED").count()

        total_database_configs = DatabaseConfig.query.count()

        # Recent audit logs
        recent_errors = AuditLog.query.filter_by(severity="ERROR").order_by(AuditLog.occurred_at.desc()).limit(10).all()
        recent_warnings = AuditLog.query.filter_by(severity="WARNING").order_by(AuditLog.occurred_at.desc()).limit(10).all()

        return {
            "migrations": {
                "total": total_migrations,
                "running": running_migrations,
                "failed": failed_migrations,
                "completed": completed_migrations,
            },
            "aws_connections": {
                "total": total_aws_connections,
                "active": active_aws_connections,
            },
            "database_configs": {
                "total": total_database_configs,
            },
            "recent_errors": [
                {
                    "event_type": log.event_type,
                    "description": log.event_description,
                    "occurred_at": log.occurred_at.isoformat(),
                }
                for log in recent_errors
            ],
            "recent_warnings": [
                {
                    "event_type": log.event_type,
                    "description": log.event_description,
                    "occurred_at": log.occurred_at.isoformat(),
                }
                for log in recent_warnings
            ],
        }

    def get_audit_logs(
        self,
        event_type: str | None = None,
        event_category: str | None = None,
        migration_id: int | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Get audit logs with optional filters."""
        query = AuditLog.query

        if event_type:
            query = query.filter_by(event_type=event_type)
        if event_category:
            query = query.filter_by(event_category=event_category)
        if migration_id:
            query = query.filter_by(migration_id=migration_id)
        if severity:
            query = query.filter_by(severity=severity)

        return query.order_by(AuditLog.occurred_at.desc()).limit(limit).offset(offset).all()

    def _log_info(self, message: str) -> None:
        """Write a structured log entry."""
        logger = self._logger or current_app.logger
        logger.info(message)
