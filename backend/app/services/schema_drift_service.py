"""Service layer for schema drift detection and comparison."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import current_app

from app.extensions import db
from app.models.database_config import DatabaseConfig
from app.models.migration import MigrationJob
from app.models.schema_snapshot import (
    SchemaSnapshot,
    SchemaDriftEvent,
    SchemaChangeType,
    SchemaChangeRisk,
)


class SchemaDriftServiceError(Exception):
    """Base exception for schema drift service errors."""


class SchemaSnapshotNotFoundError(SchemaDriftServiceError):
    """Raised when a schema snapshot cannot be located."""


class SchemaDriftValidationError(SchemaDriftServiceError):
    """Raised when schema drift configuration is invalid."""


class SchemaDriftService:
    """Coordinates schema snapshot capture and drift detection."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def capture_schema_snapshot(
        self,
        migration_id: int,
        database_config_id: int | None = None,
        snapshot_name: str | None = None,
        source_type: str = "SOURCE",
    ) -> SchemaSnapshot:
        """Capture a schema snapshot for drift detection."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise SchemaSnapshotNotFoundError(f"Migration job {migration_id} was not found.")

        if database_config_id:
            db_config = DatabaseConfig.query.get(database_config_id)
            if not db_config:
                raise SchemaSnapshotNotFoundError(f"Database config {database_config_id} was not found.")
            database_type = db_config.database_type
        else:
            database_type = "POSTGRESQL"  # Default

        # Simulate schema extraction (in production, this would query the actual database)
        schema_definition = self._extract_schema_definition(database_type, source_type)
        tables = self._extract_tables(database_type)
        indexes = self._extract_indexes(database_type)

        if not snapshot_name:
            snapshot_name = f"snapshot_{source_type.lower()}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        snapshot = SchemaSnapshot(
            migration_id=migration_id,
            database_config_id=database_config_id,
            snapshot_name=snapshot_name,
            source_type=source_type,
            database_type=database_type,
            schema_definition=json.dumps(schema_definition),
            tables=json.dumps(tables),
            indexes=json.dumps(indexes),
            captured_by="system",
        )
        db.session.add(snapshot)
        db.session.commit()

        self._log_info("Schema snapshot captured", snapshot.id, snapshot_name)
        return snapshot

    def compare_schemas(
        self,
        migration_id: int,
        snapshot_before_id: int,
        snapshot_after_id: int,
    ) -> list[SchemaDriftEvent]:
        """Compare two schema snapshots and detect drift."""
        snapshot_before = SchemaSnapshot.query.get(snapshot_before_id)
        if not snapshot_before:
            raise SchemaSnapshotNotFoundError(f"Snapshot {snapshot_before_id} was not found.")

        snapshot_after = SchemaSnapshot.query.get(snapshot_after_id)
        if not snapshot_after:
            raise SchemaSnapshotNotFoundError(f"Snapshot {snapshot_after_id} was not found.")

        schema_before = json.loads(snapshot_before.schema_definition)
        schema_after = json.loads(snapshot_after.schema_definition)

        drift_events = []

        # Detect table changes
        drift_events.extend(self._detect_table_changes(migration_id, snapshot_before_id, snapshot_after_id, schema_before, schema_after))

        # Detect column changes
        drift_events.extend(self._detect_column_changes(migration_id, snapshot_before_id, snapshot_after_id, schema_before, schema_after))

        # Detect index changes
        drift_events.extend(self._detect_index_changes(migration_id, snapshot_before_id, snapshot_after_id, schema_before, schema_after))

        # Save drift events
        for event in drift_events:
            db.session.add(event)

        db.session.commit()

        self._log_info("Schema comparison completed", f"{len(drift_events)} drift events detected")
        return drift_events

    def get_drift_events(self, migration_id: int, status: str | None = None) -> list[SchemaDriftEvent]:
        """Get schema drift events for a migration."""
        query = SchemaDriftEvent.query.filter_by(migration_id=migration_id)

        if status:
            query = query.filter_by(status=status)

        return query.order_by(SchemaDriftEvent.detected_at.desc()).all()

    def approve_drift_event(self, event_id: int, approved_by: str) -> SchemaDriftEvent:
        """Approve a schema drift event."""
        event = SchemaDriftEvent.query.get(event_id)
        if not event:
            raise SchemaSnapshotNotFoundError(f"Drift event {event_id} was not found.")

        event.status = "APPROVED"
        event.approved_by = approved_by
        event.approved_at = datetime.utcnow()
        db.session.commit()

        self._log_info("Drift event approved", event_id, approved_by)
        return event

    def reject_drift_event(self, event_id: int, rejection_reason: str, rejected_by: str) -> SchemaDriftEvent:
        """Reject a schema drift event."""
        event = SchemaDriftEvent.query.get(event_id)
        if not event:
            raise SchemaSnapshotNotFoundError(f"Drift event {event_id} was not found.")

        event.status = "REJECTED"
        event.rejection_reason = rejection_reason
        event.approved_by = rejected_by
        event.approved_at = datetime.utcnow()
        db.session.commit()

        self._log_info("Drift event rejected", event_id, rejected_by)
        return event

    def ignore_drift_event(self, event_id: int) -> SchemaDriftEvent:
        """Ignore a schema drift event."""
        event = SchemaDriftEvent.query.get(event_id)
        if not event:
            raise SchemaSnapshotNotFoundError(f"Drift event {event_id} was not found.")

        event.status = "IGNORED"
        db.session.commit()

        self._log_info("Drift event ignored", event_id)
        return event

    def _extract_schema_definition(self, database_type: str, source_type: str) -> dict[str, Any]:
        """Extract schema definition from database (simulated)."""
        # In production, this would connect to the actual database and extract schema
        return {
            "database_type": database_type,
            "source_type": source_type,
            "tables": {
                "users": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                        {"name": "name", "type": "VARCHAR(255)", "nullable": False},
                        {"name": "email", "type": "VARCHAR(255)", "nullable": False},
                        {"name": "created_at", "type": "TIMESTAMP", "nullable": False},
                    ],
                    "indexes": ["users_pkey", "users_email_idx"],
                },
                "orders": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                        {"name": "user_id", "type": "INTEGER", "nullable": False},
                        {"name": "total", "type": "DECIMAL(10,2)", "nullable": False},
                        {"name": "status", "type": "VARCHAR(50)", "nullable": False},
                    ],
                    "indexes": ["orders_pkey", "orders_user_id_idx"],
                },
            },
        }

    def _extract_tables(self, database_type: str) -> list[str]:
        """Extract table names from database (simulated)."""
        return ["users", "orders", "products", "transactions"]

    def _extract_indexes(self, database_type: str) -> list[str]:
        """Extract index names from database (simulated)."""
        return ["users_pkey", "users_email_idx", "orders_pkey", "orders_user_id_idx"]

    def _detect_table_changes(
        self,
        migration_id: int,
        snapshot_before_id: int,
        snapshot_after_id: int,
        schema_before: dict[str, Any],
        schema_after: dict[str, Any],
    ) -> list[SchemaDriftEvent]:
        """Detect table-level schema changes."""
        events = []
        tables_before = set(schema_before.get("tables", {}).keys())
        tables_after = set(schema_after.get("tables", {}).keys())

        # Detect new tables
        for table in tables_after - tables_before:
            events.append(
                SchemaDriftEvent(
                    migration_id=migration_id,
                    snapshot_before_id=snapshot_before_id,
                    snapshot_after_id=snapshot_after_id,
                    change_type=SchemaChangeType.CREATE_TABLE,
                    risk_level=SchemaChangeRisk.MODERATE,
                    table_name=table,
                    after_definition=json.dumps(schema_after["tables"][table]),
                    change_details=json.dumps({"action": "table_added", "table": table}),
                    approval_required=True,
                )
            )

        # Detect dropped tables
        for table in tables_before - tables_after:
            events.append(
                SchemaDriftEvent(
                    migration_id=migration_id,
                    snapshot_before_id=snapshot_before_id,
                    snapshot_after_id=snapshot_after_id,
                    change_type=SchemaChangeType.DROP_TABLE,
                    risk_level=SchemaChangeRisk.CRITICAL,
                    table_name=table,
                    before_definition=json.dumps(schema_before["tables"][table]),
                    change_details=json.dumps({"action": "table_dropped", "table": table}),
                    approval_required=True,
                )
            )

        return events

    def _detect_column_changes(
        self,
        migration_id: int,
        snapshot_before_id: int,
        snapshot_after_id: int,
        schema_before: dict[str, Any],
        schema_after: dict[str, Any],
    ) -> list[SchemaDriftEvent]:
        """Detect column-level schema changes."""
        events = []
        tables_before = schema_before.get("tables", {})
        tables_after = schema_after.get("tables", {})

        for table in set(tables_before.keys()) | set(tables_after.keys()):
            if table not in tables_before or table not in tables_after:
                continue

            cols_before = {col["name"]: col for col in tables_before[table].get("columns", [])}
            cols_after = {col["name"]: col for col in tables_after[table].get("columns", [])}

            # Detect new columns
            for col_name in set(cols_after.keys()) - set(cols_before.keys()):
                events.append(
                    SchemaDriftEvent(
                        migration_id=migration_id,
                        snapshot_before_id=snapshot_before_id,
                        snapshot_after_id=snapshot_after_id,
                        change_type=SchemaChangeType.ADD_COLUMN,
                        risk_level=SchemaChangeRisk.MODERATE,
                        table_name=table,
                        object_name=col_name,
                        after_definition=json.dumps(cols_after[col_name]),
                        change_details=json.dumps({"action": "column_added", "table": table, "column": col_name}),
                        approval_required=False,  # Adding columns is generally safe
                    )
                )

            # Detect dropped columns
            for col_name in set(cols_before.keys()) - set(cols_after.keys()):
                events.append(
                    SchemaDriftEvent(
                        migration_id=migration_id,
                        snapshot_before_id=snapshot_before_id,
                        snapshot_after_id=snapshot_after_id,
                        change_type=SchemaChangeType.DROP_COLUMN,
                        risk_level=SchemaChangeRisk.HIGH,
                        table_name=table,
                        object_name=col_name,
                        before_definition=json.dumps(cols_before[col_name]),
                        change_details=json.dumps({"action": "column_dropped", "table": table, "column": col_name}),
                        approval_required=True,
                    )
                )

            # Detect column type changes
            for col_name in set(cols_before.keys()) & set(cols_after.keys()):
                if cols_before[col_name]["type"] != cols_after[col_name]["type"]:
                    events.append(
                        SchemaDriftEvent(
                            migration_id=migration_id,
                            snapshot_before_id=snapshot_before_id,
                            snapshot_after_id=snapshot_after_id,
                            change_type=SchemaChangeType.ALTER_TABLE,
                            risk_level=SchemaChangeRisk.HIGH,
                            table_name=table,
                            object_name=col_name,
                            before_definition=json.dumps(cols_before[col_name]),
                            after_definition=json.dumps(cols_after[col_name]),
                            change_details=json.dumps({
                                "action": "column_altered",
                                "table": table,
                                "column": col_name,
                                "before_type": cols_before[col_name]["type"],
                                "after_type": cols_after[col_name]["type"],
                            }),
                            approval_required=True,
                        )
                    )

        return events

    def _detect_index_changes(
        self,
        migration_id: int,
        snapshot_before_id: int,
        snapshot_after_id: int,
        schema_before: dict[str, Any],
        schema_after: dict[str, Any],
    ) -> list[SchemaDriftEvent]:
        """Detect index-level schema changes."""
        events = []
        tables_before = schema_before.get("tables", {})
        tables_after = schema_after.get("tables", {})

        for table in set(tables_before.keys()) | set(tables_after.keys()):
            if table not in tables_before or table not in tables_after:
                continue

            indexes_before = set(tables_before[table].get("indexes", []))
            indexes_after = set(tables_after[table].get("indexes", []))

            # Detect new indexes
            for index in indexes_after - indexes_before:
                events.append(
                    SchemaDriftEvent(
                        migration_id=migration_id,
                        snapshot_before_id=snapshot_before_id,
                        snapshot_after_id=snapshot_after_id,
                        change_type=SchemaChangeType.CREATE_INDEX,
                        risk_level=SchemaChangeRisk.SAFE,
                        table_name=table,
                        object_name=index,
                        change_details=json.dumps({"action": "index_added", "table": table, "index": index}),
                        approval_required=False,  # Adding indexes is generally safe
                    )
                )

            # Detect dropped indexes
            for index in indexes_before - indexes_after:
                events.append(
                    SchemaDriftEvent(
                        migration_id=migration_id,
                        snapshot_before_id=snapshot_before_id,
                        snapshot_after_id=snapshot_after_id,
                        change_type=SchemaChangeType.DROP_INDEX,
                        risk_level=SchemaChangeRisk.MODERATE,
                        table_name=table,
                        object_name=index,
                        change_details=json.dumps({"action": "index_dropped", "table": table, "index": index}),
                        approval_required=True,
                    )
                )

        return events

    def _log_info(self, message: str, detail1: str | int | None = None, detail2: str | None = None) -> None:
        """Write a structured log entry."""
        logger = self._logger or current_app.logger
        if detail1 is not None and detail2 is not None:
            logger.info("%s: %s (%s)", message, detail1, detail2)
        elif detail1 is not None:
            logger.info("%s: %s", message, detail1)
        else:
            logger.info(message)
