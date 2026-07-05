"""
Purpose:
This file defines authentication-specific exceptions.

Why:
The authentication routes need a clear way to report bad input and other expected errors.

Architecture:
Auth Blueprint
↓
Auth Service
↓
Future Cognito Integration
"""


class AuthError(Exception):
    """Base class for authentication errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthValidationError(AuthError):
    """Raised when a login request contains invalid input."""
