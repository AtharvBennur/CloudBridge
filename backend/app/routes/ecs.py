"""
Purpose:
This file contains the ECS/Fargate task execution HTTP endpoints.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
ECS Blueprint
↓
ECS Service
↓
ECS Task Model
"""

from flask import Blueprint, jsonify, request

from app.exceptions.ecs import ECSTaskNotFoundError, ECSValidationError, ECSServiceError
from app.schemas.ecs import CreateECSTaskRequest, ECSTaskResponse
from app.services.ecs_service import ECSService

ecs_bp = Blueprint("ecs", __name__, url_prefix="/ecs")
ecs_service = ECSService()


@ecs_bp.errorhandler(ECSValidationError)
def handle_validation_error(error: ECSValidationError):
    """Return a validation error response for invalid ECS payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@ecs_bp.errorhandler(ECSTaskNotFoundError)
def handle_not_found_error(error: ECSTaskNotFoundError):
    """Return a not-found error response when an ECS task is missing."""
    return jsonify({"error": {"message": error.message}}), 404


@ecs_bp.errorhandler(ECSServiceError)
def handle_ecs_error(error: ECSServiceError):
    """Return a generic response for ECS service failures."""
    return jsonify({"error": {"message": error.message}}), 400


@ecs_bp.post("/tasks")
def create_ecs_task():
    """Create a new ECS task for migration execution."""
    payload = request.get_json(silent=True)
    try:
        create_request = CreateECSTaskRequest.from_payload(payload)
        task = ecs_service.create_task(
            migration_id=create_request.migration_id,
            aws_connection_id=create_request.aws_connection_id,
            cluster_arn=create_request.cluster_arn,
            task_definition_arn=create_request.task_definition_arn,
            launch_type=create_request.launch_type,
            subnet_ids=create_request.subnet_ids,
            security_group_ids=create_request.security_group_ids,
            cpu=create_request.cpu,
            memory=create_request.memory,
        )
        return jsonify(ECSTaskResponse.from_model(task).to_dict()), 201
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.post("/tasks/<int:task_id>/start")
def start_ecs_task(task_id: int):
    """Start an ECS task."""
    try:
        task = ecs_service.start_task(task_id)
        return jsonify(ECSTaskResponse.from_model(task).to_dict()), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.post("/tasks/<int:task_id>/stop")
def stop_ecs_task(task_id: int):
    """Stop a running ECS task."""
    payload = request.get_json(silent=True) or {}
    reason = payload.get("reason")
    try:
        task = ecs_service.stop_task(task_id, reason)
        return jsonify(ECSTaskResponse.from_model(task).to_dict()), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.get("/tasks/<int:task_id>/status")
def get_ecs_task_status(task_id: int):
    """Get the current status of an ECS task."""
    try:
        status = ecs_service.get_task_status(task_id)
        return jsonify(status), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.get("/tasks/<int:task_id>/logs")
def get_ecs_task_logs(task_id: int):
    """Get CloudWatch logs for an ECS task."""
    tail_lines = request.args.get("tail_lines", 100, type=int)
    try:
        logs = ecs_service.get_task_logs(task_id, tail_lines)
        return jsonify({"logs": logs}), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.post("/tasks/<int:task_id>/retry")
def retry_ecs_task(task_id: int):
    """Retry a failed ECS task."""
    try:
        task = ecs_service.retry_task(task_id)
        return jsonify(ECSTaskResponse.from_model(task).to_dict()), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.delete("/tasks/<int:task_id>")
def delete_ecs_task(task_id: int):
    """Delete an ECS task record."""
    try:
        ecs_service.delete_task(task_id)
        return jsonify({"message": "ECS task deleted successfully"}), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.get("/tasks")
def list_ecs_tasks():
    """List all ECS tasks for a migration."""
    migration_id = request.args.get("migration_id", type=int)
    
    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400
    
    from app.models.ecs_task import ECSTask
    
    tasks = ECSTask.query.filter_by(migration_id=migration_id).order_by(
        ECSTask.created_at.desc()
    ).all()
    
    return jsonify([ECSTaskResponse.from_model(task).to_dict() for task in tasks]), 200


@ecs_bp.get("/tasks/<int:task_id>")
def get_ecs_task(task_id: int):
    """Get a specific ECS task by ID."""
    from app.models.ecs_task import ECSTask
    
    task = ECSTask.query.get(task_id)
    if not task:
        return jsonify({"error": {"message": "ECS task not found"}}), 404
    
    return jsonify(ECSTaskResponse.from_model(task).to_dict()), 200
