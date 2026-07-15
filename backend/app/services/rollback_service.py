"""Service layer for rollback, resume, and recovery operations using checkpoints."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import current_app

from app.extensions import db
from app.models.migration import MigrationJob, MigrationStatus
from app.models.migration_checkpoint import MigrationCheckpoint
from app.models.cdc_config import CDCConfig
from app.models.cdc_event import CDCEvent


class RollbackServiceError(Exception):
    """Base exception for rollback service errors."""


class CheckpointNotFoundError(RollbackServiceError):
    """Raised when a checkpoint cannot be located."""


class RollbackService:
    """Coordinates rollback, resume, and recovery operations using checkpoints."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def create_rollback_checkpoint(
        self,
        migration_id: int,
        checkpoint_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> MigrationCheckpoint:
        """Create a checkpoint for potential rollback."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise RollbackServiceError(f"Migration job {migration_id} was not found.")

        checkpoint = MigrationCheckpoint(
            migration_id=migration_id,
            checkpoint_name=checkpoint_name,
            progress_percent=migration.progress_percent,
            rows_processed=migration.rows_migrated,
            checkpoint_metadata=json.dumps(metadata) if metadata else None,
        )
        db.session.add(checkpoint)
        db.session.commit()

        self._log_info(f"Rollback checkpoint created: {checkpoint_name} for migration {migration_id}")
        return checkpoint

    def rollback_to_checkpoint(self, migration_id: int, checkpoint_id: int) -> dict[str, Any]:
        """Rollback a migration to a specific checkpoint."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise RollbackServiceError(f"Migration job {migration_id} was not found.")

        checkpoint = MigrationCheckpoint.query.get(checkpoint_id)
        if not checkpoint or checkpoint.migration_id != migration_id:
            raise CheckpointNotFoundError(f"Checkpoint {checkpoint_id} not found for migration {migration_id}")

        # Restore migration state from checkpoint
        migration.progress_percent = checkpoint.progress_percent
        migration.rows_migrated = checkpoint.rows_processed
        migration.status = MigrationStatus.PENDING
        migration.error_message = None
        migration.retry_count = 0
        migration.started_at = None
        migration.completed_at = None

        # For CDC, we also need to reset CDC state
        cdc_config = CDCConfig.query.filter_by(migration_id=migration_id).first()
        if cdc_config:
            cdc_config.status = "STOPPED"
            cdc_config.last_lsn = None
            cdc_config.replication_lag_seconds = None

        db.session.commit()

        self._log_info(f"Migration {migration_id} rolled back to checkpoint {checkpoint.checkpoint_name}")

        return {
            "migration_id": migration_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint_name": checkpoint.checkpoint_name,
            "progress_percent": migration.progress_percent,
            "rows_migrated": migration.rows_migrated,
            "status": migration.status,
            "message": f"Successfully rolled back to checkpoint {checkpoint.checkpoint_name}",
        }

    def resume_from_checkpoint(self, migration_id: int, checkpoint_id: int | None = None) -> dict[str, Any]:
        """Resume a migration from the latest or specific checkpoint."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise RollbackServiceError(f"Migration job {migration_id} was not found.")

        # Get the checkpoint to resume from
        if checkpoint_id:
            checkpoint = MigrationCheckpoint.query.get(checkpoint_id)
        else:
            checkpoint = (
                MigrationCheckpoint.query.filter_by(migration_id=migration_id)
                .order_by(MigrationCheckpoint.created_at.desc())
                .first()
            )

        if not checkpoint:
            raise CheckpointNotFoundError(f"No checkpoint found for migration {migration_id}")

        # Restore migration state
        migration.progress_percent = checkpoint.progress_percent
        migration.rows_migrated = checkpoint.rows_processed
        migration.status = MigrationStatus.RUNNING
        migration.error_message = None
        migration.started_at = datetime.utcnow()
        migration.completed_at = None

        db.session.commit()

        self._log_info(f"Migration {migration_id} resumed from checkpoint {checkpoint.checkpoint_name}")

        return {
            "migration_id": migration_id,
            "checkpoint_id": checkpoint.id,
            "checkpoint_name": checkpoint.checkpoint_name,
            "progress_percent": migration.progress_percent,
            "rows_migrated": migration.rows_migrated,
            "status": migration.status,
            "message": f"Successfully resumed from checkpoint {checkpoint.checkpoint_name}",
        }

    def restart_migration(self, migration_id: int) -> dict[str, Any]:
        """Restart a migration from the beginning."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise RollbackServiceError(f"Migration job {migration_id} was not found.")

        # Reset migration state
        migration.progress_percent = 0.0
        migration.rows_migrated = 0
        migration.total_rows = None
        migration.current_table = None
        migration.status = MigrationStatus.PENDING
        migration.error_message = None
        migration.retry_count = 0
        migration.started_at = None
        migration.completed_at = None

        # Reset CDC state if exists
        cdc_config = CDCConfig.query.filter_by(migration_id=migration_id).first()
        if cdc_config:
            cdc_config.status = "STOPPED"
            cdc_config.last_lsn = None
            cdc_config.replication_lag_seconds = None
            cdc_config.consecutive_errors = 0

        # Delete all CDC events for this migration
        CDCEvent.query.filter_by(migration_id=migration_id).delete()

        db.session.commit()

        self._log_info(f"Migration {migration_id} restarted from beginning")

        return {
            "migration_id": migration_id,
            "status": migration.status,
            "progress_percent": migration.progress_percent,
            "rows_migrated": migration.rows_migrated,
            "message": "Migration successfully restarted from beginning",
        }

    def get_available_checkpoints(self, migration_id: int) -> list[MigrationCheckpoint]:
        """Get all available checkpoints for a migration."""
        return (
            MigrationCheckpoint.query.filter_by(migration_id=migration_id)
            .order_by(MigrationCheckpoint.created_at.desc())
            .all()
        )

    def get_recovery_options(self, migration_id: int) -> dict[str, Any]:
        """Get available recovery options for a failed migration."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise RollbackServiceError(f"Migration job {migration_id} was not found.")

        checkpoints = self.get_available_checkpoints(migration_id)
        latest_checkpoint = checkpoints[0] if checkpoints else None

        # Analyze CDC events for recovery
        cdc_events_total = CDCEvent.query.filter_by(migration_id=migration_id).count()
        cdc_events_processed = CDCEvent.query.filter_by(migration_id=migration_id, status="PROCESSED").count()
        cdc_events_failed = CDCEvent.query.filter_by(migration_id=migration_id, status="FAILED").count()

        recovery_options = {
            "can_rollback": latest_checkpoint is not None,
            "can_resume": latest_checkpoint is not None and migration.status in {MigrationStatus.FAILED, MigrationStatus.PAUSED},
            "can_restart": True,
            "latest_checkpoint": {
                "id": latest_checkpoint.id,
                "name": latest_checkpoint.checkpoint_name,
                "progress_percent": latest_checkpoint.progress_percent,
                "rows_processed": latest_checkpoint.rows_processed,
                "created_at": latest_checkpoint.created_at.isoformat(),
            } if latest_checkpoint else None,
            "all_checkpoints": [
                {
                    "id": cp.id,
                    "name": cp.checkpoint_name,
                    "progress_percent": cp.progress_percent,
                    "rows_processed": cp.rows_processed,
                    "created_at": cp.created_at.isoformat(),
                }
                for cp in checkpoints
            ],
            "cdc_status": {
                "total_events": cdc_events_total,
                "processed_events": cdc_events_processed,
                "failed_events": cdc_events_failed,
                "can_resume_cdc": cdc_events_failed == 0 and cdc_events_processed > 0,
            } if cdc_events_total > 0 else None,
            "current_state": {
                "status": migration.status,
                "progress_percent": migration.progress_percent,
                "rows_migrated": migration.rows_migrated,
                "error_message": migration.error_message,
            },
        }

        return recovery_options

    def delete_checkpoint(self, checkpoint_id: int) -> None:
        """Delete a checkpoint."""
        checkpoint = MigrationCheckpoint.query.get(checkpoint_id)
        if not checkpoint:
            raise CheckpointNotFoundError(f"Checkpoint {checkpoint_id} not found")

        db.session.delete(checkpoint)
        db.session.commit()

        self._log_info(f"Checkpoint {checkpoint_id} deleted")

    def cleanup_old_checkpoints(self, migration_id: int, keep_count: int = 5) -> int:
        """Cleanup old checkpoints, keeping only the most recent ones."""
        checkpoints = (
            MigrationCheckpoint.query.filter_by(migration_id=migration_id)
            .order_by(MigrationCheckpoint.created_at.desc())
            .all()
        )

        if len(checkpoints) <= keep_count:
            return 0

        # Delete oldest checkpoints
        checkpoints_to_delete = checkpoints[keep_count:]
        deleted_count = 0
        for checkpoint in checkpoints_to_delete:
            db.session.delete(checkpoint)
            deleted_count += 1

        db.session.commit()

        self._log_info(f"Cleaned up {deleted_count} old checkpoints for migration {migration_id}")
        return deleted_count

    def _log_info(self, message: str) -> None:
        """Write a structured log entry."""
        logger = self._logger or current_app.logger
        logger.info(message)
