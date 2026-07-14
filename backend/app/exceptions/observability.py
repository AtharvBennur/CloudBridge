"""Custom exceptions for observability operations."""


class ObservabilityServiceError(Exception):
    """Base exception for observability service errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ObservabilityValidationError(ObservabilityServiceError):
    """Raised when observability configuration is invalid."""
