"""Persistence model for audit logs and event tracking."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.extensions import db


class AuditEventType:
    """Supported audit event types."""

    MIGRATION_CREATED = "MIGRATION_CREATED"
    MIGRATION_STARTED = "MIGRATION_STARTED"
    MIGRATION_COMPLETED = "MIGRATION_COMPLETED"
    MIGRATION_FAILED = "MIGRATION_FAILED"
    MIGRATION_PAUSED = "MIGRATION_PAUSED"
    MIGRATION_RESUMED = "MIGRATION_RESUMED"
    MIGRATION_CANCELLED = "MIGRATION_CANCELLED"
    
    CDC_STARTED = "CDC_STARTED"
    CDC_STOPPED = "CDC_STOPPED"
    CDC_ERROR = "CDC_ERROR"
    
    SCHEMA_DRIFT_DETECTED = "SCHEMA_DRIFT_DETECTED"
    SCHEMA_APPROVAL_REQUESTED = "SCHEMA_APPROVAL_REQUESTED"
    SCHEMA_APPROVED = "SCHEMA_APPROVED"
    SCHEMA_REJECTED = "SCHEMA_REJECTED"
    
    ECS_TASK_CREATED = "ECS_TASK_CREATED"
    ECS_TASK_STARTED = "ECS_TASK_STARTED"
    ECS_TASK_STOPPED = "ECS_TASK_STOPPED"
    ECS_TASK_FAILED = "ECS_TASK_FAILED"
    
    AWS_CONNECTION_CREATED = "AWS_CONNECTION_CREATED"
    AWS_CONNECTION_CONNECTED = "AWS_CONNECTION_CONNECTED"
    AWS_CONNECTION_DISCONNECTED = "AWS_CONNECTION_DISCONNECTED"
    
    DATABASE_CONFIG_CREATED = "DATABASE_CONFIG_CREATED"
    DATABASE_CONFIG_UPDATED = "DATABASE_CONFIG_UPDATED"
    DATABASE_CONFIG_DELETED = "DATABASE_CONFIG_DELETED"
    
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"

    VALUES = {
        MIGRATION_CREATED, MIGRATION_STARTED, MIGRATION_COMPLETED, MIGRATION_FAILED,
        MIGRATION_PAUSED, MIGRATION_RESUMED, MIGRATION_CANCELLED,
        CDC_STARTED, CDC_STOPPED, CDC_ERROR,
        SCHEMA_DRIFT_DETECTED, SCHEMA_APPROVAL_REQUESTED, SCHEMA_APPROVED, SCHEMA_REJECTED,
        ECS_TASK_CREATED, ECS_TASK_STARTED, ECS_TASK_STOPPED, ECS_TASK_FAILED,
        AWS_CONNECTION_CREATED, AWS_CONNECTION_CONNECTED, AWS_CONNECTION_DISCONNECTED,
        DATABASE_CONFIG_CREATED, DATABASE_CONFIG_UPDATED, DATABASE_CONFIG_DELETED,
        USER_LOGIN, USER_LOGOUT, ERROR, WARNING, INFO,
    }


class AuditLog(db.Model):
    """Stores audit logs for system events and user actions."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    
    # Event metadata
    event_type = db.Column(db.String(64), nullable=False, index=True)
    event_category = db.Column(db.String(32), nullable=False, index=True)  # MIGRATION, CDC, SCHEMA, ECS, AWS, DATABASE, USER, SYSTEM
    
    # Related entities
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=True, index=True)
    aws_connection_id = db.Column(db.Integer, db.ForeignKey("aws_connections.id"), nullable=True, index=True)
    database_config_id = db.Column(db.Integer, db.ForeignKey("database_configs.id"), nullable=True, index=True)
    ecs_task_id = db.Column(db.Integer, db.ForeignKey("ecs_tasks.id"), nullable=True, index=True)
    
    # User context
    user_id = db.Column(db.String(255), nullable=True, index=True)
    user_email = db.Column(db.String(255), nullable=True)
    
    # Event details
    event_description = db.Column(db.Text, nullable=False)
    event_metadata = db.Column(db.Text, nullable=True)  # JSON with additional details
    
    # Request context
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    
    # Severity
    severity = db.Column(db.String(16), nullable=False, default="INFO")  # INFO, WARNING, ERROR, CRITICAL
    
    # Timestamps
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    def __repr__(self) -> str:
        return f"AuditLog(id={self.id}, event_type={self.event_type}, occurred_at={self.occurred_at})"
