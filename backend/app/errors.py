from http import HTTPStatus

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        status_code = error.code or HTTPStatus.INTERNAL_SERVER_ERROR
        response = {
            "error": {
                "code": HTTPStatus(status_code).name,
                "message": error.description,
            }
        }
        return jsonify(response), status_code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        app.logger.exception("Unhandled application error: %s", error)
        response = {
            "error": {
                "code": HTTPStatus.INTERNAL_SERVER_ERROR.name,
                "message": "An unexpected error occurred.",
            }
        }
        return jsonify(response), HTTPStatus.INTERNAL_SERVER_ERROR
