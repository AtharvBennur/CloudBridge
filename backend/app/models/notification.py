"""Persistence model for notification configuration and delivery."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.extensions import db


class NotificationType:
    """Supported notification types."""

    EMAIL = "EMAIL"
    SLACK = "SLACK"
    WEBHOOK = "WEBHOOK"

    VALUES = {EMAIL, SLACK, WEBHOOK}


class NotificationEventType:
    """Events that trigger notifications."""

    MIGRATION_COMPLETED = "MIGRATION_COMPLETED"
    MIGRATION_FAILED = "MIGRATION_FAILED"
    SCHEMA_APPROVAL_REQUIRED = "SCHEMA_APPROVAL_REQUIRED"
    WORKER_FAILURE = "WORKER_FAILURE"
    HIGH_REPLICATION_LAG = "HIGH_REPLICATION_LAG"
    SCHEMA_DRIFT_DETECTED = "SCHEMA_DRIFT_DETECTED"
    ECS_TASK_FAILED = "ECS_TASK_FAILED"

    VALUES = {
        MIGRATION_COMPLETED,
        MIGRATION_FAILED,
        SCHEMA_APPROVAL_REQUIRED,
        WORKER_FAILURE,
        HIGH_REPLICATION_LAG,
        SCHEMA_DRIFT_DETECTED,
        ECS_TASK_FAILED,
    }


class NotificationStatus:
    """Notification delivery status."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

    VALUES = {PENDING, SENT, FAILED, RETRYING}


class NotificationConfig(db.Model):
    """Stores notification configuration for users."""

    __tablename__ = "notification_configs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False, index=True)
    notification_type = db.Column(db.String(32), nullable=False)
    
    # Email configuration
    email_address = db.Column(db.String(255), nullable=True)
    
    # Slack configuration
    slack_webhook_url = db.Column(db.String(512), nullable=True)
    slack_channel = db.Column(db.String(255), nullable=True)
    
    # Webhook configuration
    webhook_url = db.Column(db.String(512), nullable=True)
    webhook_headers = db.Column(db.Text, nullable=True)  # JSON
    
    # Event subscriptions
    subscribed_events = db.Column(db.Text, nullable=True)  # JSON array of event types
    
    # Status
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return f"NotificationConfig(id={self.id}, user_id={self.user_id}, type={self.notification_type})"


class Notification(db.Model):
    """Stores individual notification delivery records."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    notification_config_id = db.Column(db.Integer, db.ForeignKey("notification_configs.id"), nullable=True, index=True)
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=True, index=True)
    
    # Event details
    event_type = db.Column(db.String(64), nullable=False, index=True)
    notification_type = db.Column(db.String(32), nullable=False)
    
    # Content
    subject = db.Column(db.String(512), nullable=True)
    body = db.Column(db.Text, nullable=True)
    payload = db.Column(db.Text, nullable=True)  # JSON
    
    # Delivery status
    status = db.Column(db.String(32), nullable=False, default=NotificationStatus.PENDING)
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    max_retries = db.Column(db.Integer, nullable=False, default=3)
    
    # Timestamps
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return f"Notification(id={self.id}, event_type={self.event_type}, status={self.status})"
