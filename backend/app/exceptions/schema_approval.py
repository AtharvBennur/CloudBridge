"""Custom exceptions for schema approval operations."""


class SchemaApprovalServiceError(Exception):
    """Base exception for schema approval service errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class SchemaApprovalValidationError(SchemaApprovalServiceError):
    """Raised when schema approval configuration is invalid."""
