"""
Purpose:
This file contains the AWS connection HTTP endpoints.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
AWS Connection Blueprint
↓
AWS Connection Service
↓
AWS Connection Model
"""

from flask import Blueprint, jsonify, request

from app.exceptions.aws_connection import (
    AWSConnectionError,
    AWSConnectionIntegrationError,
    AWSConnectionNotFoundError,
    AWSConnectionValidationError,
)
from app.middleware.auth import login_required
from app.services.aws_connection_service import AWSConnectionService
from app.services.cloudformation_service import CloudFormationService
from app.services.infrastructure_discovery_service import InfrastructureDiscoveryService, InfrastructureDiscoveryError


aws_connection_bp = Blueprint("aws_connection", __name__, url_prefix="/aws-connections")
aws_connection_service = AWSConnectionService()
cloudformation_service = CloudFormationService()
infrastructure_discovery_service = InfrastructureDiscoveryService()


@aws_connection_bp.errorhandler(AWSConnectionValidationError)
def handle_validation_error(error: AWSConnectionValidationError):
    """Return a validation error response for invalid AWS connection payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@aws_connection_bp.errorhandler(AWSConnectionNotFoundError)
def handle_not_found_error(error: AWSConnectionNotFoundError):
    """Return a not-found error response when an AWS connection is missing."""
    return jsonify({"error": {"message": error.message}}), 404


@aws_connection_bp.errorhandler(AWSConnectionError)
def handle_aws_connection_error(error: AWSConnectionError):
    """Return a generic response for AWS connection service failures."""
    status_code = 502 if isinstance(error, AWSConnectionIntegrationError) else 400
    return jsonify({"error": {"message": error.message}}), status_code


@aws_connection_bp.post('')
@login_required
def create_aws_connection():
    """Create a new AWS connection and return the stored representation."""
    payload = request.get_json(silent=True)
    response = aws_connection_service.create(payload)
    return jsonify(response.to_dict()), 201


@aws_connection_bp.get('')
@login_required
def list_aws_connections():
    """Return all AWS connections known to the system."""
    response = aws_connection_service.list()
    return jsonify([item.to_dict() for item in response]), 200


@aws_connection_bp.get('/<int:aws_connection_id>')
@login_required
def get_aws_connection(aws_connection_id: int):
    """Return a single AWS connection by its identifier."""
    response = aws_connection_service.get(aws_connection_id)
    return jsonify(response.to_dict()), 200


@aws_connection_bp.put('/<int:aws_connection_id>')
@login_required
def update_aws_connection(aws_connection_id: int):
    """Update an existing AWS connection and return the persisted record."""
    payload = request.get_json(silent=True)
    response = aws_connection_service.update(aws_connection_id, payload)
    return jsonify(response.to_dict()), 200


@aws_connection_bp.delete('/<int:aws_connection_id>')
@login_required
def delete_aws_connection(aws_connection_id: int):
    """Delete an AWS connection and return a confirmation response."""
    response = aws_connection_service.delete(aws_connection_id)
    return jsonify(response.to_dict()), 200


@aws_connection_bp.post('/connect')
@login_required
def connect_aws_connection():
    """Establish STS connection to customer AWS account."""
    payload = request.get_json(silent=True)
    response = aws_connection_service.connect(payload)
    return jsonify(response), 200


@aws_connection_bp.post('/<int:aws_connection_id>/connect')
@login_required
def connect_aws_connection_by_id(aws_connection_id: int):
    """Establish STS connection to customer AWS account by connection ID."""
    response = aws_connection_service.connect(aws_connection_id=aws_connection_id)
    return jsonify(response), 200


@aws_connection_bp.post('/validate')
@login_required
def validate_aws_connection():
    """Validate AWS connection including IAM permissions."""
    payload = request.get_json(silent=True)
    response = aws_connection_service.validate(payload)
    return jsonify(response), 200


@aws_connection_bp.post('/<int:aws_connection_id>/validate')
@login_required
def validate_aws_connection_by_id(aws_connection_id: int):
    """Validate AWS connection by connection ID."""
    response = aws_connection_service.validate(aws_connection_id=aws_connection_id)
    return jsonify(response), 200


@aws_connection_bp.post('/disconnect')
@login_required
def disconnect_aws_connection():
    """Disconnect an AWS connection."""
    payload = request.get_json(silent=True)
    response = aws_connection_service.disconnect(payload)
    return jsonify(response), 200


@aws_connection_bp.post('/<int:aws_connection_id>/disconnect')
@login_required
def disconnect_aws_connection_by_id(aws_connection_id: int):
    """Disconnect an AWS connection by connection ID."""
    response = aws_connection_service.disconnect(aws_connection_id=aws_connection_id)
    return jsonify(response), 200


@aws_connection_bp.post('/<int:aws_connection_id>/register-role-arn')
@login_required
def register_role_arn(aws_connection_id: int):
    """Register the IAM Role ARN after CloudFormation stack deployment."""
    payload = request.get_json(silent=True)
    response = aws_connection_service.register_role_arn(aws_connection_id, payload)
    return jsonify(response.to_dict()), 200


@aws_connection_bp.get('/<int:aws_connection_id>/cloudformation-template')
@login_required
def get_cloudformation_template(aws_connection_id: int):
    """Generate a downloadable CloudFormation template for customer IAM setup."""
    response = cloudformation_service.generate_template(aws_connection_id)
    return jsonify(response), 200


@aws_connection_bp.post('/<int:aws_connection_id>/infrastructure/discover')
@login_required
def discover_infrastructure(aws_connection_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        connection = infrastructure_discovery_service.discover(aws_connection_id, payload.get("stack_name"))
    except InfrastructureDiscoveryError as exc:
        return jsonify({"error": {"message": str(exc)}}), 422
    return jsonify({"status": "READY", "aws_connection_id": connection.id, "account_id": connection.aws_account_id, "region": connection.aws_region, "stack_name": connection.cloudformation_stack_name, "orchestrator_lambda_arn": connection.orchestrator_lambda_arn, "worker_lambda_arn": connection.worker_lambda_arn, "validation_lambda_arn": connection.validation_lambda_arn, "dynamodb_table_name": connection.dynamodb_table_name}), 200
