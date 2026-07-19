"""Custom exceptions for ECS operations."""


class ECSServiceError(Exception):
    """Base exception for ECS service errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ECSTaskNotFoundError(ECSServiceError):
    """Raised when an ECS task cannot be located."""


class ECSValidationError(ECSServiceError):
    """Raised when ECS configuration is invalid."""


class ECSResourceError(ECSServiceError):
    """Raised when ECS resource discovery or provisioning fails."""


class ECSPermissionError(ECSServiceError):
    """Raised when AWS IAM permissions are insufficient."""
