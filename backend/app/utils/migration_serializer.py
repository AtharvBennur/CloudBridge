"""Serialize migration jobs with Lambda execution metadata for API responses."""

from __future__ import annotations

from typing import Any

from app.models.lambda_migration import LambdaMigration
from app.models.migration import MigrationJob


def serialize_migration(migration: MigrationJob) -> dict[str, Any]:
    """Build a JSON-safe migration payload including progress and Lambda details."""
    lambda_migration = (
        LambdaMigration.query.filter_by(migration_id=migration.id)
        .order_by(LambdaMigration.id.desc())
        .first()
    )

    data: dict[str, Any] = {
        "id": migration.id,
        "job_name": migration.job_name,
        "source_database": migration.source_database,
        "destination_database": migration.destination_database,
        "status": migration.status,
        "description": migration.description,
        "aws_connection_id": migration.aws_connection_id,
        "source_database_config_id": migration.source_database_config_id,
        "destination_database_config_id": migration.destination_database_config_id,
        "progress_percent": migration.progress_percent,
        "rows_migrated": migration.rows_migrated,
        "total_rows": migration.total_rows,
        "current_table": migration.current_table,
        "error_message": migration.error_message,
        "retry_count": migration.retry_count,
        "max_retries": migration.max_retries,
        "chunk_size": migration.chunk_size,
        "created_at": migration.created_at.isoformat() if migration.created_at else "",
        "updated_at": migration.updated_at.isoformat() if migration.updated_at else "",
        "started_at": migration.started_at.isoformat() if migration.started_at else None,
        "completed_at": migration.completed_at.isoformat() if migration.completed_at else None,
        "architecture": "lambda",
    }

    if lambda_migration:
        data.update(
            {
                "lambda_migration_id": lambda_migration.id,
                "lambda_status": lambda_migration.status.value if lambda_migration.status else None,
                "chunks_created": lambda_migration.chunks_created,
                "chunks_completed": lambda_migration.chunks_completed,
                "chunks_failed": lambda_migration.chunks_failed,
                "chunks_total": lambda_migration.chunks_total or lambda_migration.chunks_created,
                "current_stage": lambda_migration.current_stage,
                "orchestrator_arn": lambda_migration.orchestrator_arn,
                "worker_arn": lambda_migration.worker_arn,
                "lambda_request_id": lambda_migration.orchestrator_request_id,
            }
        )
        if lambda_migration.error_message and not data.get("error_message"):
            data["error_message"] = lambda_migration.error_message

    return data
