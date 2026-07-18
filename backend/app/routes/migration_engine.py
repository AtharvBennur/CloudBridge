from datetime import datetime

from flask import Blueprint, jsonify, request, current_app

from app.extensions import db
from app.middleware.auth import login_required
from app.models.migration import MigrationJob, MigrationStatus
from app.models.migration_checkpoint import MigrationCheckpoint
from app.workers.manager import worker_manager

migration_engine_bp = Blueprint("migration_engine", __name__, url_prefix="/migration-engine")


@migration_engine_bp.post("/start")
@login_required
def start_migration():
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

    if migration.status in {MigrationStatus.RUNNING, MigrationStatus.COMPLETED, MigrationStatus.CANCELLED}:
        return jsonify({"error": {"message": f"Migration cannot be started from {migration.status}."}}), 409

    migration.status = MigrationStatus.QUEUED
    migration.progress_percent = 0.0
    migration.retry_count = 0
    migration.started_at = datetime.utcnow()
    db.session.commit()

    # Trigger actual background thread worker
    app_instance = current_app._get_current_object()
    if not worker_manager.start_worker(app_instance, migration.id):
        return jsonify({"error": {"message": "Migration worker is already running."}}), 409

    return jsonify({
        "migration_id": migration.id,
        "status": MigrationStatus.QUEUED,
        "message": "Migration started.",
        "checkpoint_support": True,
        "retry_support": True,
    }), 200


@migration_engine_bp.post("/checkpoint")
@login_required
def save_checkpoint():
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

    checkpoint = MigrationCheckpoint(
        migration_id=migration.id,
        checkpoint_name=payload.get("checkpoint_name", "checkpoint"),
        progress_percent=float(payload.get("progress_percent", 0.0)),
        rows_processed=int(payload.get("rows_processed", 0)),
        checkpoint_metadata=payload.get("metadata"),
    )
    db.session.add(checkpoint)
    db.session.commit()

    return jsonify({"message": "Checkpoint saved.", "checkpoint_id": checkpoint.id}), 200


@migration_engine_bp.post("/pause")
@login_required
def pause_migration():
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

    migration.status = MigrationStatus.PAUSED
    db.session.commit()

    # Pause background worker
    worker_manager.pause_worker(migration.id)

    return jsonify({"migration_id": migration.id, "status": migration.status, "message": "Migration paused."}), 200


@migration_engine_bp.post("/resume")
@login_required
def resume_migration():
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

    migration.status = MigrationStatus.RUNNING
    db.session.commit()

    # Resume background worker
    app_instance = current_app._get_current_object()
    worker_manager.resume_worker(app_instance, migration.id)

    return jsonify({"migration_id": migration.id, "status": migration.status, "message": "Migration resumed."}), 200


@migration_engine_bp.post("/retry")
@login_required
def retry_migration():
    """Retry a failed job from its latest durable checkpoint."""
    payload = request.get_json(silent=True) or {}
    migration = MigrationJob.query.get(payload.get("migration_id"))
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404
    if migration.status != MigrationStatus.FAILED:
        return jsonify({"error": {"message": "Only failed migrations can be retried."}}), 409

    migration.status = MigrationStatus.QUEUED
    migration.error_message = None
    migration.retry_count = 0
    db.session.commit()
    app_instance = current_app._get_current_object()
    if not worker_manager.retry_worker(app_instance, migration.id):
        return jsonify({"error": {"message": "Migration worker is already running."}}), 409
    return jsonify({"migration_id": migration.id, "status": MigrationStatus.QUEUED, "message": "Migration retry queued."}), 202


@migration_engine_bp.post("/cancel")
@login_required
def cancel_migration():
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

    migration.status = MigrationStatus.CANCELLED
    migration.completed_at = None
    db.session.commit()

    # Cancel background worker
    worker_manager.cancel_worker(migration.id)

    return jsonify({"migration_id": migration.id, "status": migration.status, "message": "Migration cancelled."}), 200


@migration_engine_bp.get("/<int:migration_id>/status")
@login_required
def migration_status(migration_id: int):
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

    checkpoints = MigrationCheckpoint.query.filter_by(migration_id=migration_id).order_by(MigrationCheckpoint.created_at.desc()).all()
    checkpoint_list = [{
        "id": cp.id,
        "checkpoint_name": cp.checkpoint_name,
        "progress_percent": cp.progress_percent,
        "rows_processed": cp.rows_processed,
        "metadata": cp.checkpoint_metadata,
        "created_at": cp.created_at.isoformat()
    } for cp in checkpoints]

    return jsonify({
        "migration_id": migration.id,
        "status": migration.status,
        "progress_percent": migration.progress_percent,
        "rows_migrated": migration.rows_migrated,
        "total_rows": migration.total_rows,
        "retry_count": migration.retry_count,
        "max_retries": migration.max_retries,
        "chunk_size": migration.chunk_size,
        "current_table": migration.current_table,
        "error_message": migration.error_message,
        "started_at": migration.started_at.isoformat() if migration.started_at else None,
        "completed_at": migration.completed_at.isoformat() if migration.completed_at else None,
        "checkpoints": checkpoint_list
    }), 200
