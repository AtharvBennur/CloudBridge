"""
Purpose:
This file contains the ECS/Fargate task execution HTTP endpoints.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
ECS Blueprint
↓
MigrationExecutionService (orchestrator)
↓
ECRManager → ECSManager → TaskDefinitionService → LogStreamingService
"""

import threading

from flask import Blueprint, current_app, jsonify, request

from app.exceptions.ecs import ECSTaskNotFoundError, ECSValidationError, ECSServiceError, ECSResourceError, ECSPermissionError
from app.middleware.auth import login_required
from app.schemas.ecs import CreateECSTaskRequest, ECSTaskResponse
from app.services.ecs_service import ECSService
from app.services.migration_execution_service import MigrationExecutionService
from app.services.migration_status_poller import MigrationStatusPoller

ecs_bp = Blueprint("ecs", __name__, url_prefix="/ecs")
ecs_service = ECSService()
migration_execution_service = MigrationExecutionService()
migration_status_poller = MigrationStatusPoller()


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


@ecs_bp.errorhandler(ECSResourceError)
def handle_resource_error(error: ECSResourceError):
    """Return a response for ECS resource discovery failures."""
    return jsonify({"error": {"message": error.message}}), 424


@ecs_bp.errorhandler(ECSPermissionError)
def handle_permission_error(error: ECSPermissionError):
    """Return a response for IAM permission failures."""
    return jsonify({"error": {"message": error.message}}), 403


@ecs_bp.post("/tasks")
@login_required
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
@login_required
def start_ecs_task(task_id: int):
    """Start an ECS task."""
    try:
        task = ecs_service.start_task(task_id)
        return jsonify(ECSTaskResponse.from_model(task).to_dict()), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.post("/tasks/<int:task_id>/stop")
@login_required
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
@login_required
def get_ecs_task_status(task_id: int):
    """Get the current status of an ECS task."""
    try:
        status = ecs_service.get_task_status(task_id)
        return jsonify(status), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.get("/tasks/<int:task_id>/logs")
@login_required
def get_ecs_task_logs(task_id: int):
    """Get CloudWatch logs for an ECS task."""
    tail_lines = request.args.get("tail_lines", 100, type=int)
    try:
        logs = ecs_service.get_task_logs(task_id, tail_lines)
        return jsonify({"logs": logs}), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.post("/tasks/<int:task_id>/retry")
@login_required
def retry_ecs_task(task_id: int):
    """Retry a failed ECS task."""
    try:
        task = ecs_service.retry_task(task_id)
        return jsonify(ECSTaskResponse.from_model(task).to_dict()), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.delete("/tasks/<int:task_id>")
@login_required
def delete_ecs_task(task_id: int):
    """Delete an ECS task record."""
    try:
        ecs_service.delete_task(task_id)
        return jsonify({"message": "ECS task deleted successfully"}), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.get("/tasks")
@login_required
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
@login_required
def get_ecs_task(task_id: int):
    """Get a specific ECS task by ID."""
    from app.models.ecs_task import ECSTask
    
    task = ECSTask.query.get(task_id)
    if not task:
        return jsonify({"error": {"message": "ECS task not found"}}), 404
    
    return jsonify(ECSTaskResponse.from_model(task).to_dict()), 200


@ecs_bp.post("/tasks/start-all")
@login_required
def start_all_ecs_tasks():
    """Start all PENDING ECS tasks for a migration."""
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")

    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400

    try:
        started = ecs_service.start_all_pending(int(migration_id))
        return jsonify({
            "started_count": len(started),
            "tasks": [ECSTaskResponse.from_model(t).to_dict() for t in started],
        }), 200
    except ECSServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@ecs_bp.post("/start-migration")
@login_required
def start_migration():
    """Start a migration on ECS/Fargate with full automation.

    Phase 1 (synchronous): Validate inputs, reset state, create task record.
    Phase 2 (background thread): AWS resource discovery, Docker build/push,
    task definition registration, ECS RunTask, log streaming, status polling.

    Returns 202 Accepted immediately so the frontend is not blocked waiting
    for Docker builds and AWS API calls.
    """
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    aws_connection_id = payload.get("aws_connection_id")

    if not migration_id:
        return jsonify({"error": {"message": "migration_id is required"}}), 400

    try:
        # Phase 1: fast validation + task-record creation
        task = migration_execution_service.prepare_migration(
            int(migration_id),
            aws_connection_id=int(aws_connection_id) if aws_connection_id else None,
        )

        # Phase 2: heavy AWS work in a background thread
        app = current_app._get_current_object()  # noqa: SLF001
        thread = threading.Thread(
            target=migration_execution_service.execute_migration_background,
            args=(app, task.id, int(migration_id), task.aws_connection_id),
            daemon=True,
        )
        thread.start()

        # Start background polling for task status (poller waits for RUNNING)
        migration_status_poller.start_polling(task.id)

        return jsonify({
            "message": "Migration started. Building worker image and launching ECS task…",
            "task": ECSTaskResponse.from_model(task).to_dict(),
        }), 202

    except ECSTaskNotFoundError as exc:
        return jsonify({"error": {"message": exc.message}}), 404
    except ECSPermissionError as exc:
        return jsonify({"error": {"message": exc.message}}), 403
    except ECSResourceError as exc:
        return jsonify({"error": {"message": exc.message}}), 424
    except (ECSValidationError, ECSServiceError) as exc:
        return jsonify({"error": {"message": exc.message}}), 400
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Unexpected error in start_migration")
        return jsonify({"error": {"message": f"Internal error: {str(exc)}"}}), 500
