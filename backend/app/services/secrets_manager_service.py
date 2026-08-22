"""Compatibility shim for legacy Secrets Manager references used by tests."""


class SecretManagerService:
    """Minimal no-op service kept for older patch paths and test mocks."""

    @staticmethod
    def create(*args, **kwargs):
        return {"arn": None, "name": None}

    @staticmethod
    def validate(*args, **kwargs):
        return None
