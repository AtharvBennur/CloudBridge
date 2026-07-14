"""Persistence model for CDC change events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.extensions import db


class ChangeOperation:
    """Supported change operations."""

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    VALUES = {INSERT, UPDATE, DELETE}


class CDCEventStatus:
    """CDC event processing status."""

    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

    VALUES = {PENDING, PROCESSED, FAILED, SKIPPED}


class CDCEvent(db.Model):
    """Stores individual CDC change events for tracking and replay."""

    __tablename__ = "cdc_events"

    id = db.Column(db.Integer, primary_key=True)
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=False, index=True)
    cdc_config_id = db.Column(db.Integer, db.ForeignKey("cdc_configs.id"), nullable=False, index=True)
    
    # Change metadata
    operation = db.Column(db.String(16), nullable=False)
    table_name = db.Column(db.String(255), nullable=False, index=True)
    lsn = db.Column(db.String(64), nullable=False, index=True)
    transaction_id = db.Column(db.String(64), nullable=True)
    
    # Data (stored as JSON)
    before_data = db.Column(db.Text, nullable=True)
    after_data = db.Column(db.Text, nullable=True)
    
    # Processing status
    status = db.Column(db.String(16), nullable=False, default=CDCEventStatus.PENDING)
    processed_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    
    # Timing
    change_timestamp = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return f"CDCEvent(id={self.id}, operation={self.operation}, table={self.table_name})"
