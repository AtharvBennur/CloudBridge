"""
Purpose:
This file contains the authentication service layer.

Why:
Routes should stay focused on HTTP concerns, while the service handles validation and business logic.

Architecture:
Auth Blueprint
↓
Auth Service
↓
Google OAuth Integration
"""

from __future__ import annotations

from typing import Any
import json

from flask import current_app

from app.exceptions.auth import AuthValidationError
from app.schemas.auth import AuthResponse, LoginRequest


class AuthService:
    """Coordinates authentication behavior with Google OAuth integration."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def login(self, payload: dict[str, Any] | None) -> AuthResponse:
        """Validate a login request and return authentication response."""
        try:
            login_request = LoginRequest.from_payload(payload)
        except ValueError as exc:
            raise AuthValidationError(str(exc)) from exc

        self._log_info("Login request received", login_request.email)
        
        # For now, accept any valid email/password combination
        # In production, this would integrate with Google OAuth
        return AuthResponse(
            message="Authentication successful",
            user={
                "email": login_request.email,
                "display_name": login_request.email.split("@")[0]
            }
        )

    def google_oauth_login(self, payload: dict[str, Any] | None) -> AuthResponse:
        """Handle Google OAuth login."""
        if not payload or "id_token" not in payload:
            raise AuthValidationError("Google ID token is required")
        
        # In production, verify the ID token with Google
        # For now, we'll accept the token and extract user info
        self._log_info("Google OAuth login request received")
        
        return AuthResponse(
            message="Google OAuth authentication successful",
            user={
                "email": payload.get("email", "user@gmail.com"),
                "display_name": payload.get("name", "Google User")
            }
        )

    def logout(self) -> AuthResponse:
        """Return the authentication response for a logout request."""
        self._log_info("Logout request received")
        return AuthResponse(message="Logout successful")

    def get_current_user(self) -> AuthResponse:
        """Return the authentication response for a current-user lookup."""
        self._log_info("Current user lookup requested")
        return AuthResponse(message="User session valid")

    def _log_info(self, message: str, email: str | None = None) -> None:
        """Write a structured log entry through Flask's logger when available."""
        logger = self._logger or current_app.logger
        if email:
            logger.info("%s for %s", message, email)
            return
        logger.info(message)
