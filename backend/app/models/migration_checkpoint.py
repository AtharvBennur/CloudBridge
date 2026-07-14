"""Persistence model for migration checkpoints and resume support."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.extensions import db


class MigrationCheckpoint(db.Model):
    """Represents a checkpoint captured during a migration run."""

    __tablename__ = "migration_checkpoints"

    id = db.Column(db.Integer, primary_key=True)
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=False, index=True)
    checkpoint_name = db.Column(db.String(255), nullable=False)
    progress_percent = db.Column(db.Float, nullable=False, default=0.0)
    rows_processed = db.Column(db.Integer, nullable=False, default=0)
    checkpoint_metadata = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    def __repr__(self) -> str:
        return f"MigrationCheckpoint(id={self.id}, migration_id={self.migration_id})"
