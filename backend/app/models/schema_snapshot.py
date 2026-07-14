"""Persistence model for schema snapshots and drift detection."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.extensions import db


class SchemaChangeType:
    """Supported schema change types."""

    CREATE_TABLE = "CREATE_TABLE"
    ALTER_TABLE = "ALTER_TABLE"
    DROP_TABLE = "DROP_TABLE"
    ADD_COLUMN = "ADD_COLUMN"
    DROP_COLUMN = "DROP_COLUMN"
    RENAME_COLUMN = "RENAME_COLUMN"
    CREATE_INDEX = "CREATE_INDEX"
    DROP_INDEX = "DROP_INDEX"
    ALTER_INDEX = "ALTER_INDEX"

    VALUES = {
        CREATE_TABLE,
        ALTER_TABLE,
        DROP_TABLE,
        ADD_COLUMN,
        DROP_COLUMN,
        RENAME_COLUMN,
        CREATE_INDEX,
        DROP_INDEX,
        ALTER_INDEX,
    }


class SchemaChangeRisk:
    """Risk levels for schema changes."""

    SAFE = "SAFE"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    VALUES = {SAFE, MODERATE, HIGH, CRITICAL}


class SchemaSnapshot(db.Model):
    """Stores schema snapshots for drift detection."""

    __tablename__ = "schema_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=False, index=True)
    database_config_id = db.Column(db.Integer, db.ForeignKey("database_configs.id"), nullable=True, index=True)
    
    # Snapshot metadata
    snapshot_name = db.Column(db.String(255), nullable=False)
    source_type = db.Column(db.String(32), nullable=False)  # SOURCE or DESTINATION
    database_type = db.Column(db.String(32), nullable=False)  # POSTGRESQL, MYSQL, etc.
    
    # Schema data (stored as JSON)
    schema_definition = db.Column(db.Text, nullable=False)  # Full schema definition
    tables = db.Column(db.Text, nullable=True)  # Tables list as JSON
    indexes = db.Column(db.Text, nullable=True)  # Indexes list as JSON
    
    # Metadata
    captured_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    captured_by = db.Column(db.String(255), nullable=True)  # System or user who captured
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    def __repr__(self) -> str:
        return f"SchemaSnapshot(id={self.id}, migration_id={self.migration_id}, name={self.snapshot_name})"


class SchemaDriftEvent(db.Model):
    """Stores detected schema drift events."""

    __tablename__ = "schema_drift_events"

    id = db.Column(db.Integer, primary_key=True)
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=False, index=True)
    snapshot_before_id = db.Column(db.Integer, db.ForeignKey("schema_snapshots.id"), nullable=True)
    snapshot_after_id = db.Column(db.Integer, db.ForeignKey("schema_snapshots.id"), nullable=True)
    
    # Change details
    change_type = db.Column(db.String(32), nullable=False)
    risk_level = db.Column(db.String(16), nullable=False, default=SchemaChangeRisk.MODERATE)
    table_name = db.Column(db.String(255), nullable=True, index=True)
    object_name = db.Column(db.String(255), nullable=True)  # Column name, index name, etc.
    
    # Change details (stored as JSON)
    before_definition = db.Column(db.Text, nullable=True)
    after_definition = db.Column(db.Text, nullable=True)
    change_details = db.Column(db.Text, nullable=True)  # Detailed diff as JSON
    
    # Processing status
    status = db.Column(db.String(32), nullable=False, default="DETECTED")  # DETECTED, APPROVED, REJECTED, IGNORED, APPLIED
    approval_required = db.Column(db.Boolean, nullable=False, default=True)
    
    # Approval workflow
    approved_by = db.Column(db.String(255), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Timestamps
    detected_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    def __repr__(self) -> str:
        return f"SchemaDriftEvent(id={self.id}, change_type={self.change_type}, table={self.table_name})"
