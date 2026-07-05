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
Future Cognito Integration
"""

from __future__ import annotations

from typing import Any

from flask import current_app

from app.exceptions.auth import AuthValidationError
from app.schemas.auth import AuthResponse, LoginRequest


class AuthService:
    """Coordinates authentication behavior for the current Sprint 2 architecture."""

    PENDING_COGNITO_MESSAGE = (
        "Authentication service is ready. Amazon Cognito integration will be implemented in Sprint 3."
    )

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def login(self, payload: dict[str, Any] | None) -> AuthResponse:
        """Validate a login request and return the pending authentication response."""
        try:
            login_request = LoginRequest.from_payload(payload)
        except ValueError as exc:
            raise AuthValidationError(str(exc)) from exc

        self._log_info("Login request received for pending Cognito integration", login_request.email)
        return AuthResponse(message=self.PENDING_COGNITO_MESSAGE)

    def logout(self) -> AuthResponse:
        """Return the pending authentication response for a logout request."""
        self._log_info("Logout request received for pending Cognito integration")
        return AuthResponse(message=self.PENDING_COGNITO_MESSAGE)

    def get_current_user(self) -> AuthResponse:
        """Return the pending authentication response for a current-user lookup."""
        self._log_info("Current user lookup requested for pending Cognito integration")
        return AuthResponse(message=self.PENDING_COGNITO_MESSAGE)

    def _log_info(self, message: str, email: str | None = None) -> None:
        """Write a structured log entry through Flask's logger when available."""
        logger = self._logger or current_app.logger
        if email:
            logger.info("%s for %s", message, email)
            return
        logger.info(message)
