"""Custom exceptions for schema drift operations."""


class SchemaDriftServiceError(Exception):
    """Base exception for schema drift service errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class SchemaSnapshotNotFoundError(SchemaDriftServiceError):
    """Raised when a schema snapshot cannot be located."""


class SchemaDriftValidationError(SchemaDriftServiceError):
    """Raised when schema drift configuration is invalid."""
