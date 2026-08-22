"""Compatibility wrapper for the legacy migration execution service import path."""

from app.services.lambda_migration_service import LambdaMigrationService


class MigrationExecutionService(LambdaMigrationService):
    """Backward-compatible alias used by older tests and callers."""

    pass
