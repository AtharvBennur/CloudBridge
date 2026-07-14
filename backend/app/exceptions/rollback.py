"""Custom exceptions for rollback operations."""


class RollbackServiceError(Exception):
    """Base exception for rollback service errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CheckpointNotFoundError(RollbackServiceError):
    """Raised when a checkpoint cannot be located."""


class RollbackValidationError(RollbackServiceError):
    """Raised when rollback configuration is invalid."""
