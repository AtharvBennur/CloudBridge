"""Custom exceptions for notification operations."""


class NotificationServiceError(Exception):
    """Base exception for notification service errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotificationConfigNotFoundError(NotificationServiceError):
    """Raised when a notification configuration cannot be located."""


class NotificationDeliveryError(NotificationServiceError):
    """Raised when notification delivery fails."""


class NotificationValidationError(NotificationServiceError):
    """Raised when notification configuration is invalid."""
