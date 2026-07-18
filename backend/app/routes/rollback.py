"""
Purpose:
This file contains the rollback HTTP endpoints for checkpoint-based recovery operations.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
Rollback Blueprint
↓
Rollback Service
↓
Migration Checkpoint Model
"""

from flask import Blueprint, jsonify, request

from app.exceptions.rollback import CheckpointNotFoundError, RollbackServiceError, RollbackValidationError
from app.middleware.auth import login_required
from app.services.rollback_service import RollbackService

rollback_bp = Blueprint("rollback", __name__, url_prefix="/rollback")
rollback_service = RollbackService()


@rollback_bp.errorhandler(RollbackValidationError)
def handle_validation_error(error: RollbackValidationError):
    """Return a validation error response for invalid rollback payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@rollback_bp.errorhandler(CheckpointNotFoundError)
def handle_not_found_error(error: CheckpointNotFoundError):
    """Return a not-found error response when a checkpoint is missing."""
    return jsonify({"error": {"message": error.message}}), 404


@rollback_bp.errorhandler(RollbackServiceError)
def handle_rollback_error(error: RollbackServiceError):
    """Return a generic response for rollback service failures."""
    return jsonify({"error": {"message": error.message}}), 400


@rollback_bp.post("/checkpoint")
@login_required
def create_checkpoint():
    """Create a rollback checkpoint for a migration."""
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    checkpoint_name = payload.get("checkpoint_name", "manual_checkpoint")
    metadata = payload.get("metadata")

    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400

    try:
        checkpoint = rollback_service.create_rollback_checkpoint(
            migration_id=migration_id,
            checkpoint_name=checkpoint_name,
            metadata=metadata,
        )
        return jsonify({
            "id": checkpoint.id,
            "migration_id": checkpoint.migration_id,
            "checkpoint_name": checkpoint.checkpoint_name,
            "progress_percent": checkpoint.progress_percent,
            "rows_processed": checkpoint.rows_processed,
            "created_at": checkpoint.created_at.isoformat(),
        }), 201
    except RollbackServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@rollback_bp.post("/to-checkpoint/<int:migration_id>")
@login_required
def rollback_to_checkpoint(migration_id: int):
    """Rollback a migration to a specific checkpoint."""
    payload = request.get_json(silent=True) or {}
    checkpoint_id = payload.get("checkpoint_id")

    if not checkpoint_id:
        return jsonify({"error": {"message": "checkpoint_id is required"}}), 400

    try:
        result = rollback_service.rollback_to_checkpoint(migration_id, checkpoint_id)
        return jsonify(result), 200
    except RollbackServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@rollback_bp.post("/resume/<int:migration_id>")
@login_required
def resume_from_checkpoint(migration_id: int):
    """Resume a migration from the latest or specific checkpoint."""
    payload = request.get_json(silent=True) or {}
    checkpoint_id = payload.get("checkpoint_id")

    try:
        result = rollback_service.resume_from_checkpoint(migration_id, checkpoint_id)
        return jsonify(result), 200
    except RollbackServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@rollback_bp.post("/restart/<int:migration_id>")
@login_required
def restart_migration(migration_id: int):
    """Restart a migration from the beginning."""
    try:
        result = rollback_service.restart_migration(migration_id)
        return jsonify(result), 200
    except RollbackServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@rollback_bp.get("/checkpoints/<int:migration_id>")
@login_required
def get_checkpoints(migration_id: int):
    """Get all available checkpoints for a migration."""
    try:
        checkpoints = rollback_service.get_available_checkpoints(migration_id)
        return jsonify([
            {
                "id": cp.id,
                "migration_id": cp.migration_id,
                "checkpoint_name": cp.checkpoint_name,
                "progress_percent": cp.progress_percent,
                "rows_processed": cp.rows_processed,
                "metadata": cp.checkpoint_metadata,
                "created_at": cp.created_at.isoformat(),
            }
            for cp in checkpoints
        ]), 200
    except RollbackServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@rollback_bp.get("/recovery-options/<int:migration_id>")
@login_required
def get_recovery_options(migration_id: int):
    """Get available recovery options for a migration."""
    try:
        options = rollback_service.get_recovery_options(migration_id)
        return jsonify(options), 200
    except RollbackServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@rollback_bp.delete("/checkpoint/<int:checkpoint_id>")
@login_required
def delete_checkpoint(checkpoint_id: int):
    """Delete a checkpoint."""
    try:
        rollback_service.delete_checkpoint(checkpoint_id)
        return jsonify({"message": "Checkpoint deleted successfully"}), 200
    except RollbackServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@rollback_bp.post("/cleanup-checkpoints/<int:migration_id>")
@login_required
def cleanup_checkpoints(migration_id: int):
    """Cleanup old checkpoints, keeping only the most recent ones."""
    payload = request.get_json(silent=True) or {}
    keep_count = payload.get("keep_count", 5)

    try:
        deleted_count = rollback_service.cleanup_old_checkpoints(migration_id, keep_count)
        return jsonify({
            "message": f"Cleaned up {deleted_count} old checkpoints",
            "deleted_count": deleted_count,
        }), 200
    except RollbackServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
