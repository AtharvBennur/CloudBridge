"""
Purpose:
This file contains the authentication HTTP endpoints.

Why:
Blueprints keep related APIs together and make the application easier to extend.

Architecture:
Browser
↓
Auth Blueprint
↓
Auth Service
↓
Future Cognito Integration
"""

from flask import Blueprint, jsonify, request

from app.exceptions.auth import AuthError, AuthValidationError
from app.services.auth_service import AuthService


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
auth_service = AuthService()


@auth_bp.errorhandler(AuthValidationError)
def handle_validation_error(error: AuthValidationError):
    """Return a validation error response for invalid login payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@auth_bp.errorhandler(AuthError)
def handle_auth_error(error: AuthError):
    """Return a generic error response for authentication failures."""
    return jsonify({"error": {"message": error.message}}), 400


@auth_bp.post("/login")
def login():
    """Handle a login request and return the pending Cognito response."""
    payload = request.get_json(silent=True)
    response = auth_service.login(payload)
    return jsonify(response.to_dict()), 200


@auth_bp.post("/logout")
def logout():
    """Handle a logout request and return the pending Cognito response."""
    response = auth_service.logout()
    return jsonify(response.to_dict()), 200


@auth_bp.get("/me")
def get_current_user():
    """Handle a current-user lookup and return the pending Cognito response."""
    response = auth_service.get_current_user()
    return jsonify(response.to_dict()), 200
