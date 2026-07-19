"""
Purpose:
This file contains the migration HTTP endpoints.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
Migration Blueprint
↓
Migration Service
↓
Migration Model
"""

from flask import Blueprint, jsonify, request

from app.exceptions.migration import (
    MigrationError,
    MigrationIntegrityError,
    MigrationNotFoundError,
    MigrationValidationError,
)
from app.middleware.auth import login_required
from app.services.migration_service import MigrationService


migration_bp = Blueprint("migration", __name__, url_prefix="/migrations")
migration_service = MigrationService()


@migration_bp.errorhandler(MigrationValidationError)
def handle_validation_error(error: MigrationValidationError):
    """Return a validation error response for invalid migration payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@migration_bp.errorhandler(MigrationIntegrityError)
def handle_integrity_error(error: MigrationIntegrityError):
    """Return a 422 response when referenced resources do not exist."""
    return jsonify({"error": {"message": error.message}}), 422


@migration_bp.errorhandler(MigrationNotFoundError)
def handle_not_found_error(error: MigrationNotFoundError):
    """Return a not-found error response when a migration job is missing."""
    return jsonify({"error": {"message": error.message}}), 404


@migration_bp.errorhandler(MigrationError)
def handle_migration_error(error: MigrationError):
    """Return a generic response for migration service failures."""
    return jsonify({"error": {"message": error.message}}), 400


@migration_bp.post('')
@login_required
def create_migration():
    """Create a new migration job and return the stored representation."""
    payload = request.get_json(silent=True)
    response = migration_service.create(payload)
    return jsonify(response.to_dict()), 201


@migration_bp.get('')
@login_required
def list_migrations():
    """Return all migration jobs known to the system."""
    response = migration_service.list()
    return jsonify([item.to_dict() for item in response]), 200


@migration_bp.get('/<int:migration_id>')
@login_required
def get_migration(migration_id: int):
    """Return a single migration job by its identifier."""
    response = migration_service.get(migration_id)
    return jsonify(response.to_dict()), 200


@migration_bp.put('/<int:migration_id>')
@login_required
def update_migration(migration_id: int):
    """Update an existing migration job and return the persisted record."""
    payload = request.get_json(silent=True)
    response = migration_service.update(migration_id, payload)
    return jsonify(response.to_dict()), 200


@migration_bp.delete('/<int:migration_id>')
@login_required
def delete_migration(migration_id: int):
    """Delete a migration job and return a confirmation response."""
    response = migration_service.delete(migration_id)
    return jsonify(response.to_dict()), 200
