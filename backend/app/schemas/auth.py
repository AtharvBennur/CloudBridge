"""
Purpose:
This file defines the request and response objects used by the authentication API.

Architecture:
Blueprints validate incoming JSON into schema objects.
Services receive those objects and return response objects.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LoginRequest:
    """Represents the expected login payload from the client."""

    email: str
    password: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "LoginRequest":
        """Convert raw JSON data into a validated login request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        email = payload.get("email")
        password = payload.get("password")

        if not isinstance(email, str) or not email.strip():
            raise ValueError("Email is required.")

        if not isinstance(password, str) or not password.strip():
            raise ValueError("Password is required.")

        normalized_email = email.strip().lower()
        if "@" not in normalized_email:
            raise ValueError("Email must include an @ symbol.")

        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        return cls(email=normalized_email, password=password)


@dataclass(frozen=True)
class AuthResponse:
    """Represents the structured JSON returned by authentication endpoints."""

    message: str
    user: dict[str, Any] | None = None
    token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        result = {"message": self.message}
        if self.user:
            result["user"] = self.user
        if self.token:
            result["token"] = self.token
        return result
