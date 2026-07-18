from flask import Blueprint, jsonify, request

from app.middleware.auth import login_required
from app.services.database_config_service import DatabaseConfigNotFoundError, DatabaseConfigService, DatabaseConfigValidationError


database_config_bp = Blueprint("database_config", __name__, url_prefix="/database-configs")
database_config_service = DatabaseConfigService()


@database_config_bp.errorhandler(DatabaseConfigValidationError)
def handle_validation_error(error: DatabaseConfigValidationError):
    return jsonify({"error": {"message": str(error)}}), 400


@database_config_bp.errorhandler(DatabaseConfigNotFoundError)
def handle_not_found_error(error: DatabaseConfigNotFoundError):
    return jsonify({"error": {"message": str(error)}}), 404


@database_config_bp.post('')
@login_required
def create_database_config():
    payload = request.get_json(silent=True)
    response = database_config_service.create(payload)
    return jsonify(response.to_dict()), 201


@database_config_bp.get('')
@login_required
def list_database_configs():
    response = database_config_service.list()
    return jsonify([item.to_dict() for item in response]), 200


@database_config_bp.get('/<int:database_config_id>')
@login_required
def get_database_config(database_config_id: int):
    response = database_config_service.get(database_config_id)
    return jsonify(response.to_dict()), 200


@database_config_bp.put('/<int:database_config_id>')
@login_required
def update_database_config(database_config_id: int):
    payload = request.get_json(silent=True)
    response = database_config_service.update(database_config_id, payload)
    return jsonify(response.to_dict()), 200


@database_config_bp.delete('/<int:database_config_id>')
@login_required
def delete_database_config(database_config_id: int):
    response = database_config_service.delete(database_config_id)
    return jsonify(response.to_dict()), 200


@database_config_bp.post('/aws-connections/<int:aws_connection_id>/secrets')
@login_required
def create_secret(aws_connection_id: int):
    """Create credentials directly in the selected customer's Secrets Manager."""
    response = database_config_service.create_secret(aws_connection_id, request.get_json(silent=True))
    return jsonify(response), 201


@database_config_bp.put('/aws-connections/<int:aws_connection_id>/secrets/<path:secret_id>')
@login_required
def update_secret(aws_connection_id: int, secret_id: str):
    response = database_config_service.update_secret(aws_connection_id, secret_id, request.get_json(silent=True))
    return jsonify(response), 200


@database_config_bp.post('/aws-connections/<int:aws_connection_id>/secrets/validate')
@login_required
def validate_secret(aws_connection_id: int):
    response = database_config_service.validate_secret(aws_connection_id, request.get_json(silent=True))
    return jsonify(response), 200


@database_config_bp.delete('/aws-connections/<int:aws_connection_id>/secrets/<path:secret_id>')
@login_required
def delete_secret(aws_connection_id: int, secret_id: str):
    database_config_service.delete_secret(aws_connection_id, secret_id)
    return jsonify({"message": "Secret deletion scheduled."}), 202
