"""Service layer for CDC (Change Data Capture) operations."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import current_app

from app.extensions import db
from app.models.cdc_config import CDCConfig, CDCMode, CDCStatus
from app.models.cdc_event import CDCEvent, ChangeOperation, CDCEventStatus
from app.models.migration import MigrationJob, MigrationStatus


class CDCServiceError(Exception):
    """Base exception for CDC service errors."""


class CDCConfigNotFoundError(CDCServiceError):
    """Raised when a CDC configuration cannot be located."""


class CDCValidationError(CDCServiceError):
    """Raised when CDC configuration is invalid."""


class CDCService:
    """Coordinates CDC configuration and change event tracking."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def create_config(self, migration_id: int, payload: dict[str, Any] | None = None) -> CDCConfig:
        """Create a CDC configuration for a migration job."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise CDCConfigNotFoundError(f"Migration job {migration_id} was not found.")

        # Check if CDC config already exists
        existing = CDCConfig.query.filter_by(migration_id=migration_id).first()
        if existing:
            raise CDCValidationError(f"CDC configuration already exists for migration {migration_id}.")

        config = CDCConfig(
            migration_id=migration_id,
            cdc_mode=payload.get("cdc_mode", CDCMode.FULL_LOAD_AND_CDC) if payload else CDCMode.FULL_LOAD_AND_CDC,
            replication_slot_name=payload.get("replication_slot_name") if payload else None,
            publication_name=payload.get("publication_name") if payload else None,
            batch_size=payload.get("batch_size", 1000) if payload else 1000,
            poll_interval_ms=payload.get("poll_interval_ms", 1000) if payload else 1000,
            max_lag_seconds=payload.get("max_lag_seconds", 300) if payload else 300,
        )
        db.session.add(config)
        db.session.commit()

        self._log_info("CDC configuration created", config.id, migration_id)
        return config

    def get_config(self, migration_id: int) -> CDCConfig:
        """Get CDC configuration for a migration job."""
        config = CDCConfig.query.filter_by(migration_id=migration_id).first()
        if not config:
            raise CDCConfigNotFoundError(f"CDC configuration for migration {migration_id} was not found.")
        return config

    def update_config(self, migration_id: int, payload: dict[str, Any] | None) -> CDCConfig:
        """Update CDC configuration."""
        config = self.get_config(migration_id)

        if payload:
            if "cdc_mode" in payload:
                config.cdc_mode = payload["cdc_mode"]
            if "replication_slot_name" in payload:
                config.replication_slot_name = payload["replication_slot_name"]
            if "publication_name" in payload:
                config.publication_name = payload["publication_name"]
            if "batch_size" in payload:
                config.batch_size = payload["batch_size"]
            if "poll_interval_ms" in payload:
                config.poll_interval_ms = payload["poll_interval_ms"]
            if "max_lag_seconds" in payload:
                config.max_lag_seconds = payload["max_lag_seconds"]
            if "status" in payload:
                config.status = payload["status"]

        config.updated_at = datetime.utcnow()
        db.session.commit()

        self._log_info("CDC configuration updated", config.id, migration_id)
        return config

    def delete_config(self, migration_id: int) -> None:
        """Delete CDC configuration for a migration job."""
        config = self.get_config(migration_id)
        db.session.delete(config)
        db.session.commit()
        self._log_info("CDC configuration deleted", config.id, migration_id)

    def record_change_event(
        self,
        migration_id: int,
        operation: str,
        table_name: str,
        lsn: str,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        transaction_id: str | None = None,
        change_timestamp: datetime | None = None,
    ) -> CDCEvent:
        """Record a CDC change event."""
        config = self.get_config(migration_id)

        event = CDCEvent(
            migration_id=migration_id,
            cdc_config_id=config.id,
            operation=operation,
            table_name=table_name,
            lsn=lsn,
            transaction_id=transaction_id,
            before_data=json.dumps(before_data) if before_data else None,
            after_data=json.dumps(after_data) if after_data else None,
            change_timestamp=change_timestamp,
        )
        db.session.add(event)
        db.session.commit()

        self._log_info("CDC event recorded", event.id, f"{operation} on {table_name}")
        return event

    def get_pending_events(self, migration_id: int, limit: int = 1000) -> list[CDCEvent]:
        """Get pending CDC events for processing."""
        return (
            CDCEvent.query.filter_by(migration_id=migration_id, status=CDCEventStatus.PENDING)
            .order_by(CDCEvent.lsn.asc())
            .limit(limit)
            .all()
        )

    def mark_event_processed(self, event_id: int) -> None:
        """Mark a CDC event as processed."""
        event = CDCEvent.query.get(event_id)
        if not event:
            raise CDCConfigNotFoundError(f"CDC event {event_id} was not found.")

        event.status = CDCEventStatus.PROCESSED
        event.processed_at = datetime.utcnow()
        event.updated_at = datetime.utcnow()
        db.session.commit()

    def mark_event_failed(self, event_id: int, error_message: str) -> None:
        """Mark a CDC event as failed."""
        event = CDCEvent.query.get(event_id)
        if not event:
            raise CDCConfigNotFoundError(f"CDC event {event_id} was not found.")

        event.status = CDCEventStatus.FAILED
        event.error_message = error_message
        event.retry_count += 1
        event.updated_at = datetime.utcnow()
        db.session.commit()

    def update_replication_lag(self, migration_id: int, lag_seconds: int, last_lsn: str) -> None:
        """Update replication lag metrics."""
        config = self.get_config(migration_id)
        config.replication_lag_seconds = lag_seconds
        config.last_lsn = last_lsn
        config.last_sync_at = datetime.utcnow()
        config.updated_at = datetime.utcnow()
        db.session.commit()

    def get_event_statistics(self, migration_id: int) -> dict[str, Any]:
        """Get CDC event statistics for a migration."""
        total = CDCEvent.query.filter_by(migration_id=migration_id).count()
        pending = CDCEvent.query.filter_by(migration_id=migration_id, status=CDCEventStatus.PENDING).count()
        processed = CDCEvent.query.filter_by(migration_id=migration_id, status=CDCEventStatus.PROCESSED).count()
        failed = CDCEvent.query.filter_by(migration_id=migration_id, status=CDCEventStatus.FAILED).count()

        return {
            "total_events": total,
            "pending_events": pending,
            "processed_events": processed,
            "failed_events": failed,
        }

    def _log_info(self, message: str, config_id: int | None = None, detail: str | None = None) -> None:
        """Write a structured log entry."""
        logger = self._logger or current_app.logger
        if config_id is not None and detail is not None:
            logger.info("%s for CDC config %s (%s)", message, config_id, detail)
        elif config_id is not None:
            logger.info("%s for CDC config %s", message, config_id)
        else:
            logger.info(message)
