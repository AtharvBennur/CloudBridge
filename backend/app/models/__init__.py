"""Application domain models are imported here so that Flask-SQLAlchemy can discover them."""

from app.models.aws_connection import AWSConnection
from app.models.migration import MigrationJob

__all__ = ["MigrationJob", "AWSConnection"]
