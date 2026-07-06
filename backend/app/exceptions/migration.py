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
