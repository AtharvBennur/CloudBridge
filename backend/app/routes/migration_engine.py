from datetime import datetime
import threading

from flask import Blueprint, jsonify, request, current_app

from app.extensions import db, socketio
from app.middleware.auth import login_required
from app.models.migration import MigrationJob, MigrationStatus
from app.models.migration_checkpoint import MigrationCheckpoint
from app.models.lambda_migration import LambdaMigration
from app.services.lambda_migration_service import LambdaMigrationService

migration_engine_bp = Blueprint("migration_engine", __name__, url_prefix="/migration-engine")
lambda_migration_service = LambdaMigrationService()


@migration_engine_bp.post("/start")
@login_required
def start_migration():
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    aws_connection_id = payload.get("aws_connection_id")
    if aws_connection_id is not None:
        try:
            aws_connection_id = int(aws_connection_id)
        except (TypeError, ValueError):
            return jsonify({"error": {"message": "aws_connection_id must be an integer."}}), 400
    
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

    if migration.status in {MigrationStatus.RUNNING, MigrationStatus.COMPLETED, MigrationStatus.CANCELLED}:
        return jsonify({"error": {"message": f"Migration cannot be started from {migration.status}."}}), 409

    try:
        # Prepare Lambda migration
        lambda_migration = lambda_migration_service.prepare_migration(
            migration_id=migration_id,
            aws_connection_id=aws_connection_id
        )
        
        # Trigger background execution
        app_instance = current_app._get_current_object()
        socketio.start_background_task(
            lambda_migration_service.execute_migration_background,
            app_instance, lambda_migration.id, migration_id, lambda_migration.aws_connection_id
        )

        return jsonify({
            "migration_id": migration.id,
            "lambda_migration_id": lambda_migration.id,
            "status": MigrationStatus.RUNNING,
            "message": "Migration started with Lambda execution.",
            "architecture": "lambda",
            "chunk_support": True,
            "retry_support": True,
        }), 200
    except Exception as e:
        return jsonify({"error": {"message": str(e)}}), 500


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

    # Lambda migrations don't support pause - chunks run independently
    return jsonify({"error": {"message": "Pause not supported in Lambda architecture. Chunks run independently."}}), 400


@migration_engine_bp.post("/resume")
@login_required
def resume_migration():
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

    # Lambda migrations don't support resume - chunks run independently
    return jsonify({"error": {"message": "Resume not supported in Lambda architecture. Chunks run independently."}}), 400


@migration_engine_bp.post("/retry")
@login_required
def retry_migration():
    """Retry a failed migration by re-executing Lambda workflow."""
    payload = request.get_json(silent=True) or {}
    migration = MigrationJob.query.get(payload.get("migration_id"))
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404
    if migration.status != MigrationStatus.FAILED:
        return jsonify({"error": {"message": "Only failed migrations can be retried."}}), 409

    try:
        # Reset migration state
        migration.status = MigrationStatus.QUEUED
        migration.error_message = None
        migration.retry_count = (migration.retry_count or 0) + 1
        migration.progress_percent = 0.0
        migration.rows_migrated = 0
        db.session.commit()

        # Get Lambda migration record
        lambda_migration = LambdaMigration.query.filter_by(migration_id=migration.id).first()
        if lambda_migration:
            lambda_migration.status = "PENDING"
            lambda_migration.chunks_completed = 0
            lambda_migration.chunks_failed = 0
            lambda_migration.error_message = None
            db.session.commit()

        # Trigger Lambda retry
        app_instance = current_app._get_current_object()
        effective_aws_connection_id = (
            lambda_migration.aws_connection_id if lambda_migration else migration.aws_connection_id
        )
        socketio.start_background_task(
            lambda_migration_service.execute_migration_background,
            app_instance, lambda_migration.id if lambda_migration else None, migration.id, effective_aws_connection_id
        )

        return jsonify({"migration_id": migration.id, "status": MigrationStatus.QUEUED, "message": "Migration retry with Lambda queued."}), 202
    except Exception as e:
        return jsonify({"error": {"message": str(e)}}), 500


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

    # Cancel Lambda migration if exists
    lambda_migration = LambdaMigration.query.filter_by(migration_id=migration.id).first()
    if lambda_migration:
        lambda_migration.status = "CANCELLED"
        db.session.commit()

    return jsonify({"migration_id": migration.id, "status": migration.status, "message": "Migration cancelled."}), 200


@migration_engine_bp.get("/<int:migration_id>/status")
@login_required
def migration_status(migration_id: int):
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

    # Get Lambda migration details if exists
    lambda_migration = LambdaMigration.query.filter_by(migration_id=migration_id).first()
    
    checkpoints = MigrationCheckpoint.query.filter_by(migration_id=migration_id).order_by(MigrationCheckpoint.created_at.desc()).all()
    checkpoint_list = [{
        "id": cp.id,
        "checkpoint_name": cp.checkpoint_name,
        "progress_percent": cp.progress_percent,
        "rows_processed": cp.rows_processed,
        "metadata": cp.checkpoint_metadata,
        "created_at": cp.created_at.isoformat()
    } for cp in checkpoints]

    response = {
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
        "checkpoints": checkpoint_list,
        "architecture": "lambda",
    }
    
    # Add Lambda-specific details
    if lambda_migration:
        response.update({
            "lambda_migration_id": lambda_migration.id,
            "lambda_status": lambda_migration.status.value if lambda_migration.status else None,
            "chunks_created": lambda_migration.chunks_created,
            "chunks_completed": lambda_migration.chunks_completed,
            "chunks_failed": lambda_migration.chunks_failed,
            "chunks_total": lambda_migration.chunks_total,
            "current_stage": lambda_migration.current_stage,
            "orchestrator_arn": lambda_migration.orchestrator_arn,
            "worker_arn": lambda_migration.worker_arn,
        })

    return jsonify(response), 200


@migration_engine_bp.post("/status-update")
def update_migration_status():
    """Internal endpoint called by Lambda functions to update migration progress.

    No auth required — Lambda functions run with IAM permissions.
    In production, add a shared secret or IAM-based authentication.
    """
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": "Migration job was not found."}}), 404

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

    # Update Lambda migration record if exists
    lambda_migration = LambdaMigration.query.filter_by(migration_id=migration_id).first()
    if lambda_migration:
        if "chunks_completed" in payload:
            lambda_migration.chunks_completed = payload["chunks_completed"]
        if "chunks_failed" in payload:
            lambda_migration.chunks_failed = payload["chunks_failed"]
        if "current_stage" in payload:
            lambda_migration.current_stage = payload["current_stage"]

    db.session.commit()

    # Broadcast to WebSocket listeners
    from app.services.websocket_service import websocket_service
    websocket_service.broadcast_migration_update(
        migration_id,
        {
            "status": migration.status,
            "progress_percent": migration.progress_percent,
            "rows_migrated": migration.rows_migrated,
            "error_message": migration.error_message,
        },
    )

    return jsonify({"message": "Status updated.", "migration_id": migration.id, "status": migration.status}), 200
