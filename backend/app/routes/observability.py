"""
Purpose:
This file contains the observability HTTP endpoints for metrics, logs, and audit trails.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
Observability Blueprint
↓
Observability Service
↓
Audit Log Model
"""

from flask import Blueprint, jsonify, request

from app.exceptions.observability import ObservabilityServiceError, ObservabilityValidationError
from app.services.observability_service import ObservabilityService

observability_bp = Blueprint("observability", __name__, url_prefix="/observability")
observability_service = ObservabilityService()


@observability_bp.errorhandler(ObservabilityValidationError)
def handle_validation_error(error: ObservabilityValidationError):
    """Return a validation error response for invalid observability payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@observability_bp.errorhandler(ObservabilityServiceError)
def handle_observability_error(error: ObservabilityServiceError):
    """Return a generic response for observability service failures."""
    return jsonify({"error": {"message": error.message}}), 400


@observability_bp.post("/audit-log")
def create_audit_log():
    """Create an audit log entry."""
    payload = request.get_json(silent=True) or {}
    try:
        audit_log = observability_service.log_audit_event(
            event_type=payload.get("event_type", "INFO"),
            event_category=payload.get("event_category", "SYSTEM"),
            event_description=payload.get("event_description", ""),
            migration_id=payload.get("migration_id"),
            aws_connection_id=payload.get("aws_connection_id"),
            database_config_id=payload.get("database_config_id"),
            ecs_task_id=payload.get("ecs_task_id"),
            user_id=payload.get("user_id"),
            user_email=payload.get("user_email"),
            event_metadata=payload.get("event_metadata"),
            severity=payload.get("severity", "INFO"),
        )
        return jsonify({
            "id": audit_log.id,
            "event_type": audit_log.event_type,
            "event_category": audit_log.event_category,
            "description": audit_log.event_description,
            "occurred_at": audit_log.occurred_at.isoformat(),
        }), 201
    except ObservabilityServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@observability_bp.get("/audit-logs")
def list_audit_logs():
    """List audit logs with optional filters."""
    event_type = request.args.get("event_type")
    event_category = request.args.get("event_category")
    migration_id = request.args.get("migration_id", type=int)
    severity = request.args.get("severity")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    try:
        logs = observability_service.get_audit_logs(
            event_type=event_type,
            event_category=event_category,
            migration_id=migration_id,
            severity=severity,
            limit=limit,
            offset=offset,
        )
        return jsonify([
            {
                "id": log.id,
                "event_type": log.event_type,
                "event_category": log.event_category,
                "description": log.event_description,
                "migration_id": log.migration_id,
                "user_id": log.user_id,
                "user_email": log.user_email,
                "severity": log.severity,
                "occurred_at": log.occurred_at.isoformat(),
                "ip_address": log.ip_address,
            }
            for log in logs
        ]), 200
    except ObservabilityServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@observability_bp.get("/metrics/migration/<int:migration_id>")
def get_migration_metrics(migration_id: int):
    """Get metrics for a specific migration."""
    try:
        metrics = observability_service.get_migration_metrics(migration_id)
        return jsonify(metrics), 200
    except ObservabilityServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@observability_bp.get("/metrics/system")
def get_system_metrics():
    """Get overall system health metrics."""
    try:
        metrics = observability_service.get_system_health_metrics()
        return jsonify(metrics), 200
    except ObservabilityServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@observability_bp.post("/cloudwatch/metric")
def send_cloudwatch_metric():
    """Send a custom metric to CloudWatch."""
    payload = request.get_json(silent=True) or {}
    try:
        observability_service.send_cloudwatch_metric(
            aws_connection_id=payload.get("aws_connection_id"),
            metric_name=payload.get("metric_name"),
            metric_value=payload.get("metric_value"),
            metric_namespace=payload.get("metric_namespace", "CloudBridge"),
            dimensions=payload.get("dimensions"),
            unit=payload.get("unit", "Count"),
        )
        return jsonify({"message": "Metric sent to CloudWatch"}), 200
    except ObservabilityServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@observability_bp.post("/cloudwatch/log")
def send_cloudwatch_log():
    """Send a log entry to CloudWatch Logs."""
    payload = request.get_json(silent=True) or {}
    try:
        observability_service.send_cloudwatch_log(
            aws_connection_id=payload.get("aws_connection_id"),
            log_group_name=payload.get("log_group_name"),
            log_stream_name=payload.get("log_stream_name"),
            message=payload.get("message"),
            log_level=payload.get("log_level", "INFO"),
        )
        return jsonify({"message": "Log sent to CloudWatch"}), 200
    except ObservabilityServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
