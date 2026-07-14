"""Service layer for schema approval workflow integration with migrations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import current_app

from app.extensions import db
from app.models.migration import MigrationJob, MigrationStatus
from app.models.schema_snapshot import SchemaDriftEvent, SchemaChangeRisk
from app.services.schema_drift_service import SchemaDriftService


class SchemaApprovalServiceError(Exception):
    """Base exception for schema approval service errors."""


class SchemaApprovalService:
    """Coordinates schema approval workflow with migration execution."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger
        self.schema_drift_service = SchemaDriftService(logger=logger)

    def check_and_pause_for_approval(self, migration_id: int) -> dict[str, Any]:
        """Check for pending high-risk schema changes and pause migration if needed."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise SchemaApprovalServiceError(f"Migration job {migration_id} was not found.")

        # Get pending drift events that require approval
        pending_events = self.schema_drift_service.get_drift_events(migration_id, status="DETECTED")
        high_risk_events = [e for e in pending_events if e.approval_required and e.risk_level in {SchemaChangeRisk.HIGH, SchemaChangeRisk.CRITICAL}]

        if high_risk_events:
            # Pause migration for approval
            if migration.status == MigrationStatus.RUNNING:
                migration.status = MigrationStatus.PAUSED
                db.session.commit()
                self._log_info("Migration paused for schema approval", migration_id, f"{len(high_risk_events)} high-risk events")

            return {
                "requires_approval": True,
                "migration_paused": True,
                "high_risk_events_count": len(high_risk_events),
                "events": [
                    {
                        "id": e.id,
                        "change_type": e.change_type,
                        "risk_level": e.risk_level,
                        "table_name": e.table_name,
                        "object_name": e.object_name,
                    }
                    for e in high_risk_events
                ],
            }

        return {
            "requires_approval": False,
            "migration_paused": False,
            "high_risk_events_count": 0,
            "events": [],
        }

    def approve_and_resume_migration(self, migration_id: int, event_ids: list[int], approved_by: str) -> dict[str, Any]:
        """Approve schema changes and resume migration."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise SchemaApprovalServiceError(f"Migration job {migration_id} was not found.")

        # Approve all specified events
        approved_events = []
        for event_id in event_ids:
            try:
                event = self.schema_drift_service.approve_drift_event(event_id, approved_by)
                approved_events.append(event.id)
            except Exception as exc:
                self._log_info(f"Failed to approve event {event_id}: {exc}")

        # Resume migration if it was paused
        if migration.status == MigrationStatus.PAUSED:
            migration.status = MigrationStatus.RUNNING
            db.session.commit()
            self._log_info("Migration resumed after schema approval", migration_id, approved_by)

        return {
            "approved_events": approved_events,
            "migration_resumed": True,
            "migration_status": migration.status,
        }

    def auto_apply_safe_changes(self, migration_id: int) -> dict[str, Any]:
        """Automatically apply safe schema changes without approval."""
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise SchemaApprovalServiceError(f"Migration job {migration_id} was not found.")

        # Get pending safe events
        pending_events = self.schema_drift_service.get_drift_events(migration_id, status="DETECTED")
        safe_events = [e for e in pending_events if not e.approval_required and e.risk_level == SchemaChangeRisk.SAFE]

        applied_events = []
        for event in safe_events:
            try:
                # Mark as applied (auto-approved)
                event.status = "APPLIED"
                event.approved_by = "system_auto"
                event.approved_at = datetime.utcnow()
                db.session.add(event)
                applied_events.append(event.id)
            except Exception as exc:
                self._log_info(f"Failed to auto-apply event {event.id}: {exc}")

        db.session.commit()

        self._log_info("Auto-applied safe schema changes", migration_id, f"{len(applied_events)} events")

        return {
            "applied_events": applied_events,
            "total_safe_events": len(safe_events),
        }

    def get_approval_summary(self, migration_id: int) -> dict[str, Any]:
        """Get a summary of approval status for a migration."""
        all_events = self.schema_drift_service.get_drift_events(migration_id)

        summary = {
            "total_events": len(all_events),
            "pending_approval": len([e for e in all_events if e.status == "DETECTED" and e.approval_required]),
            "approved": len([e for e in all_events if e.status == "APPROVED"]),
            "rejected": len([e for e in all_events if e.status == "REJECTED"]),
            "ignored": len([e for e in all_events if e.status == "IGNORED"]),
            "auto_applied": len([e for e in all_events if e.status == "APPLIED"]),
            "by_risk_level": {
                "SAFE": len([e for e in all_events if e.risk_level == SchemaChangeRisk.SAFE]),
                "MODERATE": len([e for e in all_events if e.risk_level == SchemaChangeRisk.MODERATE]),
                "HIGH": len([e for e in all_events if e.risk_level == SchemaChangeRisk.HIGH]),
                "CRITICAL": len([e for e in all_events if e.risk_level == SchemaChangeRisk.CRITICAL]),
            },
        }

        return summary

    def bulk_approve_by_risk(self, migration_id: int, max_risk_level: str, approved_by: str) -> dict[str, Any]:
        """Bulk approve all events up to a certain risk level."""
        risk_hierarchy = {
            SchemaChangeRisk.SAFE: 0,
            SchemaChangeRisk.MODERATE: 1,
            SchemaChangeRisk.HIGH: 2,
            SchemaChangeRisk.CRITICAL: 3,
        }

        if max_risk_level not in risk_hierarchy:
            raise SchemaApprovalServiceError(f"Invalid risk level: {max_risk_level}")

        max_level = risk_hierarchy[max_risk_level]
        pending_events = self.schema_drift_service.get_drift_events(migration_id, status="DETECTED")

        approved_events = []
        for event in pending_events:
            event_level = risk_hierarchy.get(event.risk_level, 99)
            if event_level <= max_level:
                try:
                    self.schema_drift_service.approve_drift_event(event.id, approved_by)
                    approved_events.append(event.id)
                except Exception as exc:
                    self._log_info(f"Failed to approve event {event.id}: {exc}")

        self._log_info("Bulk approved schema changes", migration_id, f"{len(approved_events)} events up to {max_risk_level}")

        return {
            "approved_events": approved_events,
            "max_risk_level": max_risk_level,
            "total_approved": len(approved_events),
        }

    def _log_info(self, message: str, migration_id: int | None = None, detail: str | None = None) -> None:
        """Write a structured log entry."""
        logger = self._logger or current_app.logger
        if migration_id is not None and detail is not None:
            logger.info("%s for migration %s (%s)", message, migration_id, detail)
        elif migration_id is not None:
            logger.info("%s for migration %s", message, migration_id)
        else:
            logger.info(message)
