"""
Purpose:
This file defines AWS connection-specific exceptions.

Why:
The AWS connection service needs a clear way to surface validation failures and missing resources.

Architecture:
AWS Connection Routes
↓
AWS Connection Service
↓
AWS Connection Error Handling
"""


class AWSConnectionError(Exception):
    """Base class for AWS connection-related errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AWSConnectionValidationError(AWSConnectionError):
    """Raised when an AWS connection request contains invalid content."""


class AWSConnectionNotFoundError(AWSConnectionError):
    """Raised when an AWS connection cannot be located by ID."""
