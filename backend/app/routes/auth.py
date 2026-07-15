"""Authentication HTTP endpoints with JWT token support."""

from flask import Blueprint, g, jsonify, request

from app.exceptions.auth import AuthError, AuthValidationError
from app.middleware.auth import login_required
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
auth_service = AuthService()


@auth_bp.errorhandler(AuthValidationError)
def handle_validation_error(error: AuthValidationError):
    return jsonify({"error": {"message": error.message}}), 400


@auth_bp.errorhandler(AuthError)
def handle_auth_error(error: AuthError):
    return jsonify({"error": {"message": error.message}}), 400


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True)
    response = auth_service.login(payload)
    return jsonify(response.to_dict()), 200


@auth_bp.post("/google-oauth")
def google_oauth_login():
    payload = request.get_json(silent=True)
    response = auth_service.google_oauth_login(payload)
    return jsonify(response.to_dict()), 200


@auth_bp.post("/logout")
@login_required
def logout():
    response = auth_service.logout()
    return jsonify(response.to_dict()), 200


@auth_bp.get("/me")
@login_required
def get_current_user():
    user = g.get("current_user", {})
    email = user.get("email") if user else None
    response = auth_service.get_current_user(email)
    return jsonify(response.to_dict()), 200
