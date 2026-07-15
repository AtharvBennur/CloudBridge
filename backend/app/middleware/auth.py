"""Authentication middleware providing JWT validation and user context."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

import jwt
from flask import current_app, g, jsonify, request


def encode_token(user_id: str, email: str, display_name: str) -> str:
    """Create a signed JWT for the given user."""
    secret = os.getenv("SECRET_KEY") or current_app.config.get("SECRET_KEY", "")
    if not secret:
        secret = "cloudbridge-dev-secret-key-do-not-use-in-production"
    payload = {
        "user_id": user_id,
        "email": email,
        "display_name": display_name,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT, returning the payload or None."""
    secret = os.getenv("SECRET_KEY") or current_app.config.get("SECRET_KEY", "")
    if not secret:
        secret = "cloudbridge-dev-secret-key-do-not-use-in-production"
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def login_required(f: Callable) -> Callable:
    """Decorator that validates JWT in the Authorization header."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": {"message": "Missing or invalid Authorization header"}}), 401

        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        if payload is None:
            return jsonify({"error": {"message": "Invalid or expired token"}}), 401

        g.current_user = payload
        return f(*args, **kwargs)

    return decorated


def get_current_user() -> dict[str, Any] | None:
    """Get the current authenticated user from the request context."""
    return g.get("current_user")
