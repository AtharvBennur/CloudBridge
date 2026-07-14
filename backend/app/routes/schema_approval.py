"""
Purpose:
This file contains the schema approval workflow HTTP endpoints.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
Schema Approval Blueprint
↓
Schema Approval Service
↓
Schema Drift Service
"""

from flask import Blueprint, jsonify, request

from app.exceptions.schema_approval import SchemaApprovalServiceError, SchemaApprovalValidationError
from app.services.schema_approval_service import SchemaApprovalService

schema_approval_bp = Blueprint("schema_approval", __name__, url_prefix="/schema-approval")
schema_approval_service = SchemaApprovalService()


@schema_approval_bp.errorhandler(SchemaApprovalValidationError)
def handle_validation_error(error: SchemaApprovalValidationError):
    """Return a validation error response for invalid schema approval payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@schema_approval_bp.errorhandler(SchemaApprovalServiceError)
def handle_schema_approval_error(error: SchemaApprovalServiceError):
    """Return a generic response for schema approval service failures."""
    return jsonify({"error": {"message": error.message}}), 400


@schema_approval_bp.post("/check/<int:migration_id>")
def check_for_approval(migration_id: int):
    """Check if migration requires schema approval and pause if needed."""
    try:
        result = schema_approval_service.check_and_pause_for_approval(migration_id)
        return jsonify(result), 200
    except SchemaApprovalServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@schema_approval_bp.post("/approve-and-resume/<int:migration_id>")
def approve_and_resume(migration_id: int):
    """Approve schema changes and resume migration."""
    payload = request.get_json(silent=True) or {}
    event_ids = payload.get("event_ids", [])
    approved_by = payload.get("approved_by", "system")

    if not event_ids:
        return jsonify({"error": {"message": "event_ids is required"}}), 400

    try:
        result = schema_approval_service.approve_and_resume_migration(migration_id, event_ids, approved_by)
        return jsonify(result), 200
    except SchemaApprovalServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@schema_approval_bp.post("/auto-apply/<int:migration_id>")
def auto_apply_safe(migration_id: int):
    """Automatically apply safe schema changes."""
    try:
        result = schema_approval_service.auto_apply_safe_changes(migration_id)
        return jsonify(result), 200
    except SchemaApprovalServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@schema_approval_bp.get("/summary/<int:migration_id>")
def get_approval_summary(migration_id: int):
    """Get approval summary for a migration."""
    try:
        summary = schema_approval_service.get_approval_summary(migration_id)
        return jsonify(summary), 200
    except SchemaApprovalServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@schema_approval_bp.post("/bulk-approve/<int:migration_id>")
def bulk_approve(migration_id: int):
    """Bulk approve schema changes up to a risk level."""
    payload = request.get_json(silent=True) or {}
    max_risk_level = payload.get("max_risk_level", "MODERATE")
    approved_by = payload.get("approved_by", "system")

    try:
        result = schema_approval_service.bulk_approve_by_risk(migration_id, max_risk_level, approved_by)
        return jsonify(result), 200
    except SchemaApprovalServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
