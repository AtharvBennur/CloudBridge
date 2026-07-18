"""
Purpose:
This file contains the CDC HTTP endpoints.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
CDC Blueprint
↓
CDC Service
↓
CDC Model
"""

from flask import Blueprint, jsonify, request

from app.exceptions.cdc import CDCConfigNotFoundError, CDCValidationError, CDCServiceError
from app.middleware.auth import login_required
from app.schemas.cdc import CDCConfigResponse, CreateCDCConfigRequest, UpdateCDCConfigRequest, CDCEventResponse
from app.services.cdc_service import CDCService
from app.workers.manager import worker_manager

cdc_bp = Blueprint("cdc", __name__, url_prefix="/cdc")
cdc_service = CDCService()


@cdc_bp.errorhandler(CDCValidationError)
def handle_validation_error(error: CDCValidationError):
    """Return a validation error response for invalid CDC payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@cdc_bp.errorhandler(CDCConfigNotFoundError)
def handle_not_found_error(error: CDCConfigNotFoundError):
    """Return a not-found error response when a CDC configuration is missing."""
    return jsonify({"error": {"message": error.message}}), 404


@cdc_bp.errorhandler(CDCServiceError)
def handle_cdc_error(error: CDCServiceError):
    """Return a generic response for CDC service failures."""
    return jsonify({"error": {"message": error.message}}), 400


@cdc_bp.post("/config")
@login_required
def create_cdc_config():
    """Create a new CDC configuration for a migration job."""
    payload = request.get_json(silent=True)
    migration_id = payload.get("migration_id") if payload else None
    
    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400
    
    try:
        config = cdc_service.create_config(migration_id, payload)
        return jsonify(CDCConfigResponse.from_model(config).to_dict()), 201
    except CDCServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@cdc_bp.get("/config/<int:migration_id>")
@login_required
def get_cdc_config(migration_id: int):
    """Get CDC configuration for a migration job."""
    try:
        config = cdc_service.get_config(migration_id)
        return jsonify(CDCConfigResponse.from_model(config).to_dict()), 200
    except CDCServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 404


@cdc_bp.put("/config/<int:migration_id>")
@login_required
def update_cdc_config(migration_id: int):
    """Update CDC configuration for a migration job."""
    payload = request.get_json(silent=True)
    try:
        config = cdc_service.update_config(migration_id, payload)
        return jsonify(CDCConfigResponse.from_model(config).to_dict()), 200
    except CDCServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@cdc_bp.delete("/config/<int:migration_id>")
@login_required
def delete_cdc_config(migration_id: int):
    """Delete CDC configuration for a migration job."""
    try:
        cdc_service.delete_config(migration_id)
        return jsonify({"message": "CDC configuration deleted successfully"}), 200
    except CDCServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 404


@cdc_bp.post("/start")
@login_required
def start_cdc():
    """Start CDC replication for a migration job."""
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    
    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400
    
    try:
        config = cdc_service.get_config(migration_id)
        config.status = "RUNNING"
        
        from app.extensions import db
        from app.models.migration import MigrationJob, MigrationStatus
        from app import create_app
        
        job = MigrationJob.query.get(migration_id)
        if not job:
            return jsonify({"error": {"message": "Migration job not found"}}), 404
        
        job.status = MigrationStatus.RUNNING
        db.session.commit()
        
        # Start CDC worker
        app_instance = create_app()
        from app.workers.cdc_worker import PostgreSQLCDCWorker
        worker = PostgreSQLCDCWorker(app_instance, migration_id)
        worker_manager._workers[migration_id] = worker
        worker.start()
        
        return jsonify({
            "migration_id": migration_id,
            "status": "RUNNING",
            "message": "CDC replication started",
            "cdc_mode": config.cdc_mode,
        }), 200
    except CDCServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@cdc_bp.post("/pause")
@login_required
def pause_cdc():
    """Pause CDC replication for a migration job."""
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    
    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400
    
    try:
        config = cdc_service.get_config(migration_id)
        config.status = "PAUSED"
        
        from app.extensions import db
        db.session.commit()
        
        worker_manager.pause_worker(migration_id)
        
        return jsonify({
            "migration_id": migration_id,
            "status": "PAUSED",
            "message": "CDC replication paused",
        }), 200
    except CDCServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@cdc_bp.post("/resume")
@login_required
def resume_cdc():
    """Resume CDC replication for a migration job."""
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    
    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400
    
    try:
        config = cdc_service.get_config(migration_id)
        config.status = "RUNNING"
        
        from app.extensions import db
        from app import create_app
        
        db.session.commit()
        
        app_instance = create_app()
        worker_manager.resume_worker(app_instance, migration_id)
        
        return jsonify({
            "migration_id": migration_id,
            "status": "RUNNING",
            "message": "CDC replication resumed",
        }), 200
    except CDCServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@cdc_bp.post("/stop")
@login_required
def stop_cdc():
    """Stop CDC replication for a migration job."""
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    
    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400
    
    try:
        config = cdc_service.get_config(migration_id)
        config.status = "STOPPED"
        
        from app.extensions import db
        db.session.commit()
        
        worker_manager.cancel_worker(migration_id)
        
        return jsonify({
            "migration_id": migration_id,
            "status": "STOPPED",
            "message": "CDC replication stopped",
        }), 200
    except CDCServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@cdc_bp.get("/events/<int:migration_id>")
@login_required
def get_cdc_events(migration_id: int):
    """Get CDC events for a migration job."""
    try:
        from app.models.cdc_event import CDCEvent, CDCEventStatus
        
        status_filter = request.args.get("status")
        limit = request.args.get("limit", 100, type=int)
        
        query = CDCEvent.query.filter_by(migration_id=migration_id)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        events = query.order_by(CDCEvent.created_at.desc()).limit(limit).all()
        
        return jsonify([CDCEventResponse.from_model(event).to_dict() for event in events]), 200
    except Exception as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@cdc_bp.get("/statistics/<int:migration_id>")
@login_required
def get_cdc_statistics(migration_id: int):
    """Get CDC statistics for a migration job."""
    try:
        stats = cdc_service.get_event_statistics(migration_id)
        return jsonify(stats), 200
    except CDCServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
