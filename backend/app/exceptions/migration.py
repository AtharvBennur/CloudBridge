"""
Purpose:
This file defines migration-specific exceptions.

Why:
The migration service needs a clear way to surface validation failures and missing resources.

Architecture:
Migration Routes
↓
Migration Service
↓
Migration Error Handling
"""


class MigrationError(Exception):
    """Base class for migration-related errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MigrationValidationError(MigrationError):
    """Raised when a migration request contains invalid content."""


class MigrationNotFoundError(MigrationError):
    """Raised when a migration job cannot be located by ID."""


class MigrationIntegrityError(MigrationError):
    """Raised when a referenced foreign key does not exist."""


class LambdaExecutionError(MigrationError):
    """Raised when Lambda function execution fails."""

    def __init__(self, message: str, details: dict = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class LambdaValidationError(MigrationError):
    """Raised when Lambda validation fails."""

    def __init__(self, message: str, validation_errors: list = None) -> None:
        super().__init__(message)
        self.message = message
        self.validation_errors = validation_errors or []


# Convenience functions for creating lambda errors
def lambda_execution_error(message: str, details: dict = None) -> LambdaExecutionError:
    """Create a Lambda execution error."""
    return LambdaExecutionError(message, details)


def lambda_validation_error(message: str, validation_errors: list = None) -> LambdaValidationError:
    """Create a Lambda validation error."""
    return LambdaValidationError(message, validation_errors)
