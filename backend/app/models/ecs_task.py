"""Persistence model for ECS/Fargate task execution."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.extensions import db


class ECSTaskStatus:
    """Supported ECS task status values."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"

    VALUES = {PENDING, RUNNING, STOPPED, FAILED, SUCCEEDED}


class ECSTask(db.Model):
    """Stores ECS/Fargate task execution metadata."""

    __tablename__ = "ecs_tasks"

    id = db.Column(db.Integer, primary_key=True)
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=False, index=True)
    aws_connection_id = db.Column(db.Integer, db.ForeignKey("aws_connections.id"), nullable=True, index=True)
    
    # ECS task metadata
    task_arn = db.Column(db.String(512), nullable=True, unique=True)
    task_definition_arn = db.Column(db.String(512), nullable=True)
    cluster_arn = db.Column(db.String(512), nullable=True)
    
    # Execution configuration
    launch_type = db.Column(db.String(32), nullable=False, default="FARGATE")  # FARGATE or EC2
    platform_version = db.Column(db.String(32), nullable=True)
    subnet_ids = db.Column(db.Text, nullable=True)  # JSON array
    security_group_ids = db.Column(db.Text, nullable=True)  # JSON array
    
    # Task status
    status = db.Column(db.String(32), nullable=False, default=ECSTaskStatus.PENDING)
    desired_status = db.Column(db.String(32), nullable=True)
    
    # Resource allocation
    cpu = db.Column(db.String(16), nullable=False, default="256")
    memory = db.Column(db.String(16), nullable=False, default="512")
    
    # Execution metadata
    started_at = db.Column(db.DateTime, nullable=True)
    stopped_at = db.Column(db.DateTime, nullable=True)
    exit_code = db.Column(db.Integer, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    stop_reason = db.Column(db.Text, nullable=True)
    
    # Retry configuration
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    max_retries = db.Column(db.Integer, nullable=False, default=3)
    
    # Logging
    log_group_name = db.Column(db.String(255), nullable=True)
    log_stream_name = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return f"ECSTask(id={self.id}, migration_id={self.migration_id}, status={self.status})"
