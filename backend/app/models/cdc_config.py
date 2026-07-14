"""Persistence model for CDC (Change Data Capture) configuration."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.extensions import db


class CDCMode:
    """Supported CDC replication modes."""

    FULL_LOAD = "FULL_LOAD"
    CDC_ONLY = "CDC_ONLY"
    FULL_LOAD_AND_CDC = "FULL_LOAD_AND_CDC"

    VALUES = {FULL_LOAD, CDC_ONLY, FULL_LOAD_AND_CDC}


class CDCStatus:
    """CDC replication status values."""

    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    COMPLETED = "COMPLETED"

    VALUES = {INITIALIZING, RUNNING, PAUSED, STOPPED, ERROR, COMPLETED}


class CDCConfig(db.Model):
    """Stores CDC configuration for a migration job."""

    __tablename__ = "cdc_configs"

    id = db.Column(db.Integer, primary_key=True)
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=False, unique=True, index=True)
    cdc_mode = db.Column(db.String(32), nullable=False, default=CDCMode.FULL_LOAD_AND_CDC)
    replication_slot_name = db.Column(db.String(255), nullable=True)
    publication_name = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(32), nullable=False, default=CDCStatus.INITIALIZING)
    
    # CDC timing and lag metrics
    last_lsn = db.Column(db.String(64), nullable=True)
    last_sync_at = db.Column(db.DateTime, nullable=True)
    replication_lag_seconds = db.Column(db.Integer, nullable=True)
    
    # Configuration
    batch_size = db.Column(db.Integer, nullable=False, default=1000)
    poll_interval_ms = db.Column(db.Integer, nullable=False, default=1000)
    max_lag_seconds = db.Column(db.Integer, nullable=False, default=300)
    
    # Error handling
    error_message = db.Column(db.Text, nullable=True)
    consecutive_errors = db.Column(db.Integer, nullable=False, default=0)
    max_consecutive_errors = db.Column(db.Integer, nullable=False, default=10)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return f"CDCConfig(id={self.id}, migration_id={self.migration_id}, mode={self.cdc_mode})"
