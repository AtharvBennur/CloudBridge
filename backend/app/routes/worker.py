"""Internal Worker API — endpoints called exclusively by ECS migration worker containers.

Authentication: shared WORKER_API_SECRET header (X-Worker-Secret) instead of user JWT.
These endpoints are NOT meant to be called by the frontend.
"""

from __future__ import annotations

import os
from datetime import datetime
from functools import wraps
from typing import Any, Callable

from flask import Blueprint, g, jsonify, request

from app.extensions import db
from app.models.migration import MigrationJob, MigrationStatus
from app.models.migration_checkpoint import MigrationCheckpoint
from app.services.websocket_service import websocket_service

worker_bp = Blueprint("worker", __name__, url_prefix="/worker")

# ── Shared-secret auth ─────────────────────────────────────────────────────


def _get_worker_secret() -> str:
    """Return the configured worker secret, falling back to SECRET_KEY."""
    from flask import current_app
    val = (
        current_app.config.get("WORKER_API_SECRET")
        or current_app.config.get("SECRET_KEY")
        or "cloudbridge-worker-secret"
    )
    return val.strip() if isinstance(val, str) else val


def worker_required(f: Callable) -> Callable:
    """Decorator that validates X-Worker-Secret header."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        provided = request.headers.get("X-Worker-Secret", "").strip()
        expected = _get_worker_secret()
        if not provided or provided != expected:
            return jsonify({"error": {"message": "Unauthorized: invalid worker secret"}}), 401
        return f(*args, **kwargs)

    return decorated


# ── Endpoints ──────────────────────────────────────────────────────────────


@worker_bp.get("/migrations/<int:migration_id>")
@worker_required
def get_migration(migration_id: int):
    """Fetch migration job details (used by the ECS worker at startup)."""
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": f"Migration {migration_id} not found."}}), 404

    return jsonify({
        "id": migration.id,
        "job_name": migration.job_name,
        "status": migration.status,
        "source_database": migration.source_database,
        "destination_database": migration.destination_database,
        "rows_migrated": migration.rows_migrated or 0,
        "total_rows": migration.total_rows,
        "progress_percent": migration.progress_percent or 0.0,
        "error_message": migration.error_message,
    }), 200


@worker_bp.post("/migrations/<int:migration_id>/checkpoint")
@worker_required
def save_checkpoint(migration_id: int):
    """Save a migration checkpoint (called after each batch)."""
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": f"Migration {migration_id} not found."}}), 404

    payload = request.get_json(silent=True) or {}
    checkpoint = MigrationCheckpoint(
        migration_id=migration_id,
        checkpoint_name=payload.get("checkpoint_name", "checkpoint"),
        progress_percent=float(payload.get("progress_percent", 0.0)),
        rows_processed=int(payload.get("rows_processed", 0)),
        checkpoint_metadata=payload.get("metadata"),
    )
    db.session.add(checkpoint)
    db.session.commit()

    return jsonify({"message": "Checkpoint saved.", "checkpoint_id": checkpoint.id}), 200


@worker_bp.post("/migrations/<int:migration_id>/status")
@worker_required
def update_status(migration_id: int):
    """Update migration status (called by worker on progress, completion, or failure)."""
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": f"Migration {migration_id} not found."}}), 404

    payload = request.get_json(silent=True) or {}

    status = payload.get("status")
    if status and status in MigrationStatus.VALUES:
        migration.status = status

    if "progress_percent" in payload:
        migration.progress_percent = float(payload["progress_percent"])
    if "rows_migrated" in payload:
        migration.rows_migrated = int(payload["rows_migrated"])
    if "error" in payload:
        migration.error_message = payload["error"]
    if status == "COMPLETED":
        migration.completed_at = datetime.utcnow()
        migration.progress_percent = 100.0
    if status == "FAILED":
        migration.completed_at = datetime.utcnow()

    db.session.commit()

    websocket_service.broadcast_migration_update(
        migration_id,
        {
            "status": migration.status,
            "progress_percent": migration.progress_percent,
            "rows_migrated": migration.rows_migrated,
            "error_message": migration.error_message,
        },
    )

    return jsonify({
        "message": "Status updated.",
        "migration_id": migration.id,
        "status": migration.status,
    }), 200
