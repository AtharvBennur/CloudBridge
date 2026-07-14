"""Request and response schemas for CDC endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.cdc_config import CDCConfig, CDCMode, CDCStatus
from app.models.cdc_event import CDCEvent


@dataclass(frozen=True)
class CreateCDCConfigRequest:
    """Represents the payload required to create a CDC configuration."""

    cdc_mode: str
    replication_slot_name: str | None = None
    publication_name: str | None = None
    batch_size: int = 1000
    poll_interval_ms: int = 1000
    max_lag_seconds: int = 300

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "CreateCDCConfigRequest":
        """Convert raw JSON into a validated creation request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        cdc_mode = payload.get("cdc_mode", CDCMode.FULL_LOAD_AND_CDC)
        replication_slot_name = payload.get("replication_slot_name")
        publication_name = payload.get("publication_name")
        batch_size = payload.get("batch_size", 1000)
        poll_interval_ms = payload.get("poll_interval_ms", 1000)
        max_lag_seconds = payload.get("max_lag_seconds", 300)

        if cdc_mode not in CDCMode.VALUES:
            raise ValueError(f"CDC mode must be one of: {', '.join(CDCMode.VALUES)}")

        try:
            batch_size = int(batch_size)
            poll_interval_ms = int(poll_interval_ms)
            max_lag_seconds = int(max_lag_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("Batch size, poll interval, and max lag must be integers.") from exc

        if batch_size <= 0:
            raise ValueError("Batch size must be positive.")
        if poll_interval_ms <= 0:
            raise ValueError("Poll interval must be positive.")
        if max_lag_seconds <= 0:
            raise ValueError("Max lag seconds must be positive.")

        return cls(
            cdc_mode=cdc_mode,
            replication_slot_name=replication_slot_name,
            publication_name=publication_name,
            batch_size=batch_size,
            poll_interval_ms=poll_interval_ms,
            max_lag_seconds=max_lag_seconds,
        )


@dataclass(frozen=True)
class UpdateCDCConfigRequest:
    """Represents the payload used to update a CDC configuration."""

    cdc_mode: str | None = None
    replication_slot_name: str | None = None
    publication_name: str | None = None
    status: str | None = None
    batch_size: int | None = None
    poll_interval_ms: int | None = None
    max_lag_seconds: int | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "UpdateCDCConfigRequest":
        """Convert raw JSON into a validated update request object."""
        if payload is None:
            return cls()

        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        cdc_mode = payload.get("cdc_mode")
        replication_slot_name = payload.get("replication_slot_name")
        publication_name = payload.get("publication_name")
        status = payload.get("status")
        batch_size = payload.get("batch_size")
        poll_interval_ms = payload.get("poll_interval_ms")
        max_lag_seconds = payload.get("max_lag_seconds")

        if cdc_mode is not None and cdc_mode not in CDCMode.VALUES:
            raise ValueError(f"CDC mode must be one of: {', '.join(CDCMode.VALUES)}")

        if status is not None and status not in CDCStatus.VALUES:
            raise ValueError(f"Status must be one of: {', '.join(CDCStatus.VALUES)}")

        try:
            if batch_size is not None:
                batch_size = int(batch_size)
            if poll_interval_ms is not None:
                poll_interval_ms = int(poll_interval_ms)
            if max_lag_seconds is not None:
                max_lag_seconds = int(max_lag_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("Batch size, poll interval, and max lag must be integers.") from exc

        return cls(
            cdc_mode=cdc_mode,
            replication_slot_name=replication_slot_name,
            publication_name=publication_name,
            status=status,
            batch_size=batch_size,
            poll_interval_ms=poll_interval_ms,
            max_lag_seconds=max_lag_seconds,
        )


@dataclass(frozen=True)
class CDCConfigResponse:
    """Represents the structured JSON returned by CDC endpoints."""

    id: int
    migration_id: int
    cdc_mode: str
    replication_slot_name: str | None
    publication_name: str | None
    status: str
    last_lsn: str | None
    last_sync_at: str | None
    replication_lag_seconds: int | None
    batch_size: int
    poll_interval_ms: int
    max_lag_seconds: int
    error_message: str | None
    consecutive_errors: int
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        return {
            "id": self.id,
            "migration_id": self.migration_id,
            "cdc_mode": self.cdc_mode,
            "replication_slot_name": self.replication_slot_name,
            "publication_name": self.publication_name,
            "status": self.status,
            "last_lsn": self.last_lsn,
            "last_sync_at": self.last_sync_at,
            "replication_lag_seconds": self.replication_lag_seconds,
            "batch_size": self.batch_size,
            "poll_interval_ms": self.poll_interval_ms,
            "max_lag_seconds": self.max_lag_seconds,
            "error_message": self.error_message,
            "consecutive_errors": self.consecutive_errors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_model(cls, config: CDCConfig) -> "CDCConfigResponse":
        """Build a response DTO from a persisted CDC configuration."""
        return cls(
            id=config.id,
            migration_id=config.migration_id,
            cdc_mode=config.cdc_mode,
            replication_slot_name=config.replication_slot_name,
            publication_name=config.publication_name,
            status=config.status,
            last_lsn=config.last_lsn,
            last_sync_at=config.last_sync_at.isoformat() if config.last_sync_at else None,
            replication_lag_seconds=config.replication_lag_seconds,
            batch_size=config.batch_size,
            poll_interval_ms=config.poll_interval_ms,
            max_lag_seconds=config.max_lag_seconds,
            error_message=config.error_message,
            consecutive_errors=config.consecutive_errors,
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else "",
        )


@dataclass(frozen=True)
class CDCEventResponse:
    """Represents a CDC change event response."""

    id: int
    migration_id: int
    cdc_config_id: int
    operation: str
    table_name: str
    lsn: str
    transaction_id: str | None
    before_data: dict[str, Any] | None
    after_data: dict[str, Any] | None
    status: str
    processed_at: str | None
    error_message: str | None
    retry_count: int
    change_timestamp: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        return {
            "id": self.id,
            "migration_id": self.migration_id,
            "cdc_config_id": self.cdc_config_id,
            "operation": self.operation,
            "table_name": self.table_name,
            "lsn": self.lsn,
            "transaction_id": self.transaction_id,
            "before_data": self.before_data,
            "after_data": self.after_data,
            "status": self.status,
            "processed_at": self.processed_at,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "change_timestamp": self.change_timestamp,
            "created_at": self.created_at,
        }

    @classmethod
    def from_model(cls, event: CDCEvent) -> "CDCEventResponse":
        """Build a response DTO from a persisted CDC event."""
        import json

        return cls(
            id=event.id,
            migration_id=event.migration_id,
            cdc_config_id=event.cdc_config_id,
            operation=event.operation,
            table_name=event.table_name,
            lsn=event.lsn,
            transaction_id=event.transaction_id,
            before_data=json.loads(event.before_data) if event.before_data else None,
            after_data=json.loads(event.after_data) if event.after_data else None,
            status=event.status,
            processed_at=event.processed_at.isoformat() if event.processed_at else None,
            error_message=event.error_message,
            retry_count=event.retry_count,
            change_timestamp=event.change_timestamp.isoformat() if event.change_timestamp else None,
            created_at=event.created_at.isoformat() if event.created_at else "",
        )
