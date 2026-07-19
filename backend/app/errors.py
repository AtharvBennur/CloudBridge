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
from app.services.secrets_manager_service import SecretManagerError


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

    @app.errorhandler(SecretManagerError)
    def handle_secret_manager_error(error: SecretManagerError):
        app.logger.error("Secrets Manager error [%s]: %s", error.code, error.message)
        status = 404 if error.code == "SECRET_NOT_FOUND" else 400 if error.code in ("ROLE_ARN_MISSING", "STS_ERROR") else 502
        response = {
            "error": {
                "code": error.code,
                "message": error.message,
                "status": status,
            }
        }
        return jsonify(response), status

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
