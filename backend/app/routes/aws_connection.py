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

from app.exceptions.aws_connection import AWSConnectionError, AWSConnectionNotFoundError, AWSConnectionValidationError
from app.services.aws_connection_service import AWSConnectionService


aws_connection_bp = Blueprint("aws_connection", __name__, url_prefix="/aws-connections")
aws_connection_service = AWSConnectionService()


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
    return jsonify({"error": {"message": error.message}}), 400


@aws_connection_bp.post("")
def create_aws_connection():
    """Create a new AWS connection and return the stored representation."""
    payload = request.get_json(silent=True)
    response = aws_connection_service.create(payload)
    return jsonify(response.to_dict()), 201


@aws_connection_bp.get("")
def list_aws_connections():
    """Return all AWS connections known to the system."""
    response = aws_connection_service.list()
    return jsonify([item.to_dict() for item in response]), 200


@aws_connection_bp.get("/<int:aws_connection_id>")
def get_aws_connection(aws_connection_id: int):
    """Return a single AWS connection by its identifier."""
    response = aws_connection_service.get(aws_connection_id)
    return jsonify(response.to_dict()), 200


@aws_connection_bp.put("/<int:aws_connection_id>")
def update_aws_connection(aws_connection_id: int):
    """Update an existing AWS connection and return the persisted record."""
    payload = request.get_json(silent=True)
    response = aws_connection_service.update(aws_connection_id, payload)
    return jsonify(response.to_dict()), 200


@aws_connection_bp.delete("/<int:aws_connection_id>")
def delete_aws_connection(aws_connection_id: int):
    """Delete an AWS connection and return a confirmation response."""
    response = aws_connection_service.delete(aws_connection_id)
    return jsonify(response.to_dict()), 200


@aws_connection_bp.post("/connect")
def connect_aws_connection():
    """Placeholder endpoint for future STS connection integration."""
    response = aws_connection_service.connect()
    return jsonify(response), 200


@aws_connection_bp.post("/validate")
def validate_aws_connection():
    """Placeholder endpoint for future STS validation integration."""
    response = aws_connection_service.validate()
    return jsonify(response), 200


@aws_connection_bp.post("/disconnect")
def disconnect_aws_connection():
    """Placeholder endpoint for future STS disconnection integration."""
    response = aws_connection_service.disconnect()
    return jsonify(response), 200
