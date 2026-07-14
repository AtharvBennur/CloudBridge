"""Request and response schemas for schema drift endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.models.schema_snapshot import SchemaSnapshot, SchemaDriftEvent


@dataclass(frozen=True)
class CreateSnapshotRequest:
    """Represents the payload required to create a schema snapshot."""

    migration_id: int
    database_config_id: int | None = None
    snapshot_name: str | None = None
    source_type: str = "SOURCE"

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "CreateSnapshotRequest":
        """Convert raw JSON into a validated creation request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        migration_id = payload.get("migration_id")
        database_config_id = payload.get("database_config_id")
        snapshot_name = payload.get("snapshot_name")
        source_type = payload.get("source_type", "SOURCE")

        if not migration_id:
            raise ValueError("migration_id is required.")

        try:
            migration_id = int(migration_id)
            if database_config_id is not None:
                database_config_id = int(database_config_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("migration_id and database_config_id must be integers.") from exc

        if source_type not in {"SOURCE", "DESTINATION"}:
            raise ValueError("source_type must be either SOURCE or DESTINATION.")

        return cls(
            migration_id=migration_id,
            database_config_id=database_config_id,
            snapshot_name=snapshot_name,
            source_type=source_type,
        )


@dataclass(frozen=True)
class CompareSchemasRequest:
    """Represents the payload required to compare schema snapshots."""

    migration_id: int
    snapshot_before_id: int
    snapshot_after_id: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "CompareSchemasRequest":
        """Convert raw JSON into a validated comparison request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        migration_id = payload.get("migration_id")
        snapshot_before_id = payload.get("snapshot_before_id")
        snapshot_after_id = payload.get("snapshot_after_id")

        if not migration_id or not snapshot_before_id or not snapshot_after_id:
            raise ValueError("migration_id, snapshot_before_id, and snapshot_after_id are required.")

        try:
            migration_id = int(migration_id)
            snapshot_before_id = int(snapshot_before_id)
            snapshot_after_id = int(snapshot_after_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("All IDs must be integers.") from exc

        return cls(
            migration_id=migration_id,
            snapshot_before_id=snapshot_before_id,
            snapshot_after_id=snapshot_after_id,
        )


@dataclass(frozen=True)
class ApproveDriftRequest:
    """Represents the payload required to approve a drift event."""

    approved_by: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "ApproveDriftRequest":
        """Convert raw JSON into a validated approval request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        approved_by = payload.get("approved_by")

        if not approved_by or not isinstance(approved_by, str):
            raise ValueError("approved_by is required and must be a string.")

        return cls(approved_by=approved_by.strip())


@dataclass(frozen=True)
class RejectDriftRequest:
    """Represents the payload required to reject a drift event."""

    rejection_reason: str
    rejected_by: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "RejectDriftRequest":
        """Convert raw JSON into a validated rejection request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        rejection_reason = payload.get("rejection_reason")
        rejected_by = payload.get("rejected_by")

        if not rejection_reason or not isinstance(rejection_reason, str):
            raise ValueError("rejection_reason is required and must be a string.")
        if not rejected_by or not isinstance(rejected_by, str):
            raise ValueError("rejected_by is required and must be a string.")

        return cls(
            rejection_reason=rejection_reason.strip(),
            rejected_by=rejected_by.strip(),
        )


@dataclass(frozen=True)
class SchemaSnapshotResponse:
    """Represents the structured JSON returned by schema snapshot endpoints."""

    id: int
    migration_id: int
    database_config_id: int | None
    snapshot_name: str
    source_type: str
    database_type: str
    schema_definition: dict[str, Any]
    tables: list[str] | None
    indexes: list[str] | None
    captured_at: str
    captured_by: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        return {
            "id": self.id,
            "migration_id": self.migration_id,
            "database_config_id": self.database_config_id,
            "snapshot_name": self.snapshot_name,
            "source_type": self.source_type,
            "database_type": self.database_type,
            "schema_definition": self.schema_definition,
            "tables": self.tables,
            "indexes": self.indexes,
            "captured_at": self.captured_at,
            "captured_by": self.captured_by,
            "created_at": self.created_at,
        }

    @classmethod
    def from_model(cls, snapshot: SchemaSnapshot) -> "SchemaSnapshotResponse":
        """Build a response DTO from a persisted schema snapshot."""
        return cls(
            id=snapshot.id,
            migration_id=snapshot.migration_id,
            database_config_id=snapshot.database_config_id,
            snapshot_name=snapshot.snapshot_name,
            source_type=snapshot.source_type,
            database_type=snapshot.database_type,
            schema_definition=json.loads(snapshot.schema_definition) if snapshot.schema_definition else {},
            tables=json.loads(snapshot.tables) if snapshot.tables else None,
            indexes=json.loads(snapshot.indexes) if snapshot.indexes else None,
            captured_at=snapshot.captured_at.isoformat() if snapshot.captured_at else "",
            captured_by=snapshot.captured_by,
            created_at=snapshot.created_at.isoformat() if snapshot.created_at else "",
        )


@dataclass(frozen=True)
class SchemaDriftEventResponse:
    """Represents a schema drift event response."""

    id: int
    migration_id: int
    snapshot_before_id: int | None
    snapshot_after_id: int | None
    change_type: str
    risk_level: str
    table_name: str | None
    object_name: str | None
    before_definition: dict[str, Any] | None
    after_definition: dict[str, Any] | None
    change_details: dict[str, Any] | None
    status: str
    approval_required: bool
    approved_by: str | None
    approved_at: str | None
    rejection_reason: str | None
    detected_at: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        return {
            "id": self.id,
            "migration_id": self.migration_id,
            "snapshot_before_id": self.snapshot_before_id,
            "snapshot_after_id": self.snapshot_after_id,
            "change_type": self.change_type,
            "risk_level": self.risk_level,
            "table_name": self.table_name,
            "object_name": self.object_name,
            "before_definition": self.before_definition,
            "after_definition": self.after_definition,
            "change_details": self.change_details,
            "status": self.status,
            "approval_required": self.approval_required,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "rejection_reason": self.rejection_reason,
            "detected_at": self.detected_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_model(cls, event: SchemaDriftEvent) -> "SchemaDriftEventResponse":
        """Build a response DTO from a persisted schema drift event."""
        return cls(
            id=event.id,
            migration_id=event.migration_id,
            snapshot_before_id=event.snapshot_before_id,
            snapshot_after_id=event.snapshot_after_id,
            change_type=event.change_type,
            risk_level=event.risk_level,
            table_name=event.table_name,
            object_name=event.object_name,
            before_definition=json.loads(event.before_definition) if event.before_definition else None,
            after_definition=json.loads(event.after_definition) if event.after_definition else None,
            change_details=json.loads(event.change_details) if event.change_details else None,
            status=event.status,
            approval_required=event.approval_required,
            approved_by=event.approved_by,
            approved_at=event.approved_at.isoformat() if event.approved_at else None,
            rejection_reason=event.rejection_reason,
            detected_at=event.detected_at.isoformat() if event.detected_at else "",
            created_at=event.created_at.isoformat() if event.created_at else "",
        )
