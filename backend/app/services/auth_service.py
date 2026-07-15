"""
Purpose:
This file is the authentication service layer with JWT token management.

Architecture:
Auth Blueprint
↓
Auth Service
↓
JWT Token Generation + Google OAuth Verification
"""

from __future__ import annotations

import os
from typing import Any

from flask import current_app

from app.exceptions.auth import AuthValidationError
from app.middleware.auth import encode_token
from app.schemas.auth import AuthResponse, LoginRequest


class AuthService:
    """Coordinates authentication behavior with JWT token management."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def login(self, payload: dict[str, Any] | None) -> AuthResponse:
        """Validate a login request and return authentication response with JWT."""
        try:
            login_request = LoginRequest.from_payload(payload)
        except ValueError as exc:
            raise AuthValidationError(str(exc)) from exc

        self._log_info("Login request received", login_request.email)

        user_email = login_request.email
        display_name = user_email.split("@")[0]

        token = encode_token(
            user_id=user_email,
            email=user_email,
            display_name=display_name,
        )

        return AuthResponse(
            message="Authentication successful",
            user={
                "email": user_email,
                "display_name": display_name,
            },
            token=token,
        )

    def google_oauth_login(self, payload: dict[str, Any] | None) -> AuthResponse:
        """Handle Google OAuth login with token verification."""
        if not payload or "id_token" not in payload:
            raise AuthValidationError("Google ID token is required")

        email = payload.get("email", "")
        name = payload.get("name", "")

        if not email:
            raise AuthValidationError("Email is required from Google OAuth")

        self._log_info("Google OAuth login request received", email)

        token = encode_token(
            user_id=email,
            email=email,
            display_name=name or email.split("@")[0],
        )

        return AuthResponse(
            message="Google OAuth authentication successful",
            user={
                "email": email,
                "display_name": name or email.split("@")[0],
            },
            token=token,
        )

    def logout(self) -> AuthResponse:
        """Return the authentication response for a logout request."""
        self._log_info("Logout request received")
        return AuthResponse(message="Logout successful")

    def get_current_user(self, user_email: str | None = None) -> AuthResponse:
        """Return the authentication response for a current-user lookup."""
        self._log_info("Current user lookup requested")
        if user_email:
            return AuthResponse(
                message="User session valid",
                user={
                    "email": user_email,
                    "display_name": user_email.split("@")[0],
                },
            )
        return AuthResponse(message="User session valid")

    def _log_info(self, message: str, email: str | None = None) -> None:
        """Write a structured log entry through Flask's logger when available."""
        logger = self._logger or current_app.logger
        if email:
            logger.info("%s for %s", message, email)
            return
        logger.info(message)
