"""
Purpose:
This file defines the SQLAlchemy model for migration jobs.

Why:
The backend needs a persistent representation for migration metadata that can be created, listed, updated, and deleted.

Architecture:
Flask Application Factory
↓
SQLAlchemy Model
↓
Migration Service
↓
Migration Routes
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.extensions import db


class MigrationStatus:
    """Centralizes the supported migration job statuses."""

    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    VALUES = {PENDING, QUEUED, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED}


class MigrationJob(db.Model):
    """Represents a migration job and its metadata."""

    __tablename__ = "migration_jobs"

    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(255), nullable=False, index=True)
    source_database = db.Column(db.String(255), nullable=False)
    destination_database = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=MigrationStatus.PENDING)
    description = db.Column(db.Text, nullable=True)
    aws_connection_id = db.Column(db.Integer, db.ForeignKey("aws_connections.id"), nullable=True, index=True)
    source_database_config_id = db.Column(db.Integer, db.ForeignKey("database_configs.id"), nullable=True)
    destination_database_config_id = db.Column(db.Integer, db.ForeignKey("database_configs.id"), nullable=True)
    progress_percent = db.Column(db.Float, nullable=False, default=0.0)
    rows_migrated = db.Column(db.Integer, nullable=False, default=0)
    total_rows = db.Column(db.Integer, nullable=True)
    current_table = db.Column(db.String(255), nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    max_retries = db.Column(db.Integer, nullable=False, default=3)
    chunk_size = db.Column(db.Integer, nullable=False, default=1000)
    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        """Provide a readable representation for debugging and logs."""
        return f"MigrationJob(id={self.id}, job_name={self.job_name!r})"
