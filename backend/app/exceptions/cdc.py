"""Custom exceptions for CDC operations."""


class CDCServiceError(Exception):
    """Base exception for CDC service errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CDCConfigNotFoundError(CDCServiceError):
    """Raised when a CDC configuration cannot be located."""


class CDCValidationError(CDCServiceError):
    """Raised when CDC configuration is invalid."""
