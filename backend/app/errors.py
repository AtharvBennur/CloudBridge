import traceback

from http import HTTPStatus

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from app.exceptions.aws_connection import (
    AWSConnectionError,
    AWSConnectionIntegrationError,
    AWSConnectionNotFoundError,
    AWSConnectionValidationError,
)


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

    @app.errorhandler(AWSConnectionValidationError)
    def handle_aws_validation_error(error: AWSConnectionValidationError):
        app.logger.warning("AWS validation error: %s", error.message)
        response = {
            "error": {
                "code": "AWS_VALIDATION_ERROR",
                "message": error.message,
                "status": 400,
            }
        }
        return jsonify(response), 400

    @app.errorhandler(AWSConnectionNotFoundError)
    def handle_aws_not_found_error(error: AWSConnectionNotFoundError):
        response = {
            "error": {
                "code": "AWS_CONNECTION_NOT_FOUND",
                "message": error.message,
                "status": 404,
            }
        }
        return jsonify(response), 404

    @app.errorhandler(AWSConnectionIntegrationError)
    def handle_aws_integration_error(error: AWSConnectionIntegrationError):
        app.logger.error("AWS integration error: %s", error.message)
        response = {
            "error": {
                "code": "AWS_INTEGRATION_ERROR",
                "message": error.message,
                "status": 502,
            }
        }
        return jsonify(response), 502

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        tb = traceback.format_exc()
        app.logger.error("Unhandled application error: %s\n%s", error, tb)
        
        # Extract specific error detail
        error_name = type(error).__name__
        error_msg = str(error) or "An internal error occurred."
        
        response = {
            "error": {
                "code": error_name,
                "message": error_msg,
                "problem": f"Backend encountered an unhandled exception: {error_name}",
                "cause": error_msg,
                "suggested_fix": "Inspect the backend logs for the full stack trace or check resource permissions.",
                "traceback": tb,
                "status": HTTPStatus.INTERNAL_SERVER_ERROR,
            }
        }
        return jsonify(response), HTTPStatus.INTERNAL_SERVER_ERROR
