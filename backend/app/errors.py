import traceback

from http import HTTPStatus

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        status_code = error.code or HTTPStatus.INTERNAL_SERVER_ERROR
        app.logger.warning(
            "HTTP %s %s -> %s",
            getattr(request, "method", "?"),
            getattr(request, "path", "?"),
            status_code,
        )
        response = {
            "error": {
                "code": HTTPStatus(status_code).name,
                "message": error.description,
                "status": status_code,
            }
        }
        return jsonify(response), status_code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        tb = traceback.format_exc()
        app.logger.error("Unhandled application error: %s\n%s", error, tb)
        response = {
            "error": {
                "code": HTTPStatus.INTERNAL_SERVER_ERROR.name,
                "message": "An unexpected error occurred.",
                "status": HTTPStatus.INTERNAL_SERVER_ERROR,
            }
        }
        return jsonify(response), HTTPStatus.INTERNAL_SERVER_ERROR
