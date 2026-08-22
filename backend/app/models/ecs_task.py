from __future__ import annotations

from datetime import datetime

from app.extensions import db


class ECSTaskStatus:
    """Backward-compatible status values kept for older ECS-based tests."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ECSTask(db.Model):
    """Compatibility shim for legacy ECS task tracking in older integration tests."""

    __tablename__ = "ecs_tasks"

    id = db.Column(db.Integer, primary_key=True)
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=True)
    task_arn = db.Column(db.String(512), nullable=True)
    container_name = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(32), nullable=False, default=ECSTaskStatus.PENDING)
    started_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
