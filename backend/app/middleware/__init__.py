"""Middleware package for CloudBridge backend.

Provides request-level middleware for authentication, request ID tracking,
and request/response logging.
"""

from __future__ import annotations

import uuid
from typing import Any

from flask import Flask, g, request


class RequestMiddleware:
    """Register request-level middleware on the Flask application."""

    def __init__(self, app: Flask | None = None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    @staticmethod
    def _before_request() -> None:
        g.request_id = str(uuid.uuid4())
        g.start_time = __import__("time").time()

    @staticmethod
    def _after_request(response: Any) -> Any:
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id
        return response
