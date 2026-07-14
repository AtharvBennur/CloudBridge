"""
Purpose:
This file contains the schema drift detection HTTP endpoints.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
Schema Drift Blueprint
↓
Schema Drift Service
↓
Schema Snapshot Model
"""

from flask import Blueprint, jsonify, request

from app.exceptions.schema_drift import SchemaSnapshotNotFoundError, SchemaDriftValidationError, SchemaDriftServiceError
from app.schemas.schema_drift import (
    CreateSnapshotRequest,
    CompareSchemasRequest,
    ApproveDriftRequest,
    RejectDriftRequest,
    SchemaSnapshotResponse,
    SchemaDriftEventResponse,
)
from app.services.schema_drift_service import SchemaDriftService

schema_drift_bp = Blueprint("schema_drift", __name__, url_prefix="/schema-drift")
schema_drift_service = SchemaDriftService()


@schema_drift_bp.errorhandler(SchemaDriftValidationError)
def handle_validation_error(error: SchemaDriftValidationError):
    """Return a validation error response for invalid schema drift payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@schema_drift_bp.errorhandler(SchemaSnapshotNotFoundError)
def handle_not_found_error(error: SchemaSnapshotNotFoundError):
    """Return a not-found error response when a schema snapshot is missing."""
    return jsonify({"error": {"message": error.message}}), 404


@schema_drift_bp.errorhandler(SchemaDriftServiceError)
def handle_schema_drift_error(error: SchemaDriftServiceError):
    """Return a generic response for schema drift service failures."""
    return jsonify({"error": {"message": error.message}}), 400


@schema_drift_bp.post("/snapshots")
def create_snapshot():
    """Create a new schema snapshot."""
    payload = request.get_json(silent=True)
    try:
        create_request = CreateSnapshotRequest.from_payload(payload)
        snapshot = schema_drift_service.capture_schema_snapshot(
            migration_id=create_request.migration_id,
            database_config_id=create_request.database_config_id,
            snapshot_name=create_request.snapshot_name,
            source_type=create_request.source_type,
        )
        return jsonify(SchemaSnapshotResponse.from_model(snapshot).to_dict()), 201
    except SchemaDriftServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@schema_drift_bp.get("/snapshots/<int:snapshot_id>")
def get_snapshot(snapshot_id: int):
    """Get a schema snapshot by ID."""
    from app.models.schema_snapshot import SchemaSnapshot
    
    snapshot = SchemaSnapshot.query.get(snapshot_id)
    if not snapshot:
        return jsonify({"error": {"message": "Schema snapshot not found"}}), 404
    
    return jsonify(SchemaSnapshotResponse.from_model(snapshot).to_dict()), 200


@schema_drift_bp.get("/snapshots")
def list_snapshots():
    """List all schema snapshots for a migration."""
    migration_id = request.args.get("migration_id", type=int)
    
    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400
    
    from app.models.schema_snapshot import SchemaSnapshot
    
    snapshots = SchemaSnapshot.query.filter_by(migration_id=migration_id).order_by(
        SchemaSnapshot.captured_at.desc()
    ).all()
    
    return jsonify([SchemaSnapshotResponse.from_model(s).to_dict() for s in snapshots]), 200


@schema_drift_bp.post("/compare")
def compare_schemas():
    """Compare two schema snapshots and detect drift."""
    payload = request.get_json(silent=True)
    try:
        compare_request = CompareSchemasRequest.from_payload(payload)
        drift_events = schema_drift_service.compare_schemas(
            migration_id=compare_request.migration_id,
            snapshot_before_id=compare_request.snapshot_before_id,
            snapshot_after_id=compare_request.snapshot_after_id,
        )
        return jsonify([SchemaDriftEventResponse.from_model(event).to_dict() for event in drift_events]), 200
    except SchemaDriftServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@schema_drift_bp.get("/drift-events")
def list_drift_events():
    """List schema drift events for a migration."""
    migration_id = request.args.get("migration_id", type=int)
    status = request.args.get("status")
    
    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400
    
    try:
        events = schema_drift_service.get_drift_events(migration_id, status)
        return jsonify([SchemaDriftEventResponse.from_model(event).to_dict() for event in events]), 200
    except SchemaDriftServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@schema_drift_bp.get("/drift-events/<int:event_id>")
def get_drift_event(event_id: int):
    """Get a specific drift event by ID."""
    from app.models.schema_snapshot import SchemaDriftEvent
    
    event = SchemaDriftEvent.query.get(event_id)
    if not event:
        return jsonify({"error": {"message": "Drift event not found"}}), 404
    
    return jsonify(SchemaDriftEventResponse.from_model(event).to_dict()), 200


@schema_drift_bp.post("/drift-events/<int:event_id>/approve")
def approve_drift_event(event_id: int):
    """Approve a schema drift event."""
    payload = request.get_json(silent=True)
    try:
        approve_request = ApproveDriftRequest.from_payload(payload)
        event = schema_drift_service.approve_drift_event(event_id, approve_request.approved_by)
        return jsonify(SchemaDriftEventResponse.from_model(event).to_dict()), 200
    except SchemaDriftServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@schema_drift_bp.post("/drift-events/<int:event_id>/reject")
def reject_drift_event(event_id: int):
    """Reject a schema drift event."""
    payload = request.get_json(silent=True)
    try:
        reject_request = RejectDriftRequest.from_payload(payload)
        event = schema_drift_service.reject_drift_event(event_id, reject_request.rejection_reason, reject_request.rejected_by)
        return jsonify(SchemaDriftEventResponse.from_model(event).to_dict()), 200
    except SchemaDriftServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@schema_drift_bp.post("/drift-events/<int:event_id>/ignore")
def ignore_drift_event(event_id: int):
    """Ignore a schema drift event."""
    try:
        event = schema_drift_service.ignore_drift_event(event_id)
        return jsonify(SchemaDriftEventResponse.from_model(event).to_dict()), 200
    except SchemaDriftServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
