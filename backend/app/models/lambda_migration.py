"""Lambda Migration Model - tracks Lambda-based migration execution."""

from datetime import datetime
from enum import Enum

from app.extensions import db


class LambdaMigrationStatus(Enum):
    """Status of Lambda migration execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LambdaMigration(db.Model):
    """Model for tracking Lambda-based migration execution."""
    
    __tablename__ = "lambda_migrations"
    
    id = db.Column(db.Integer, primary_key=True)
    migration_id = db.Column(db.Integer, db.ForeignKey("migration_jobs.id"), nullable=False)
    aws_connection_id = db.Column(db.Integer, db.ForeignKey("aws_connections.id"), nullable=False)
    
    # Lambda execution details
    status = db.Column(db.Enum(LambdaMigrationStatus), default=LambdaMigrationStatus.PENDING, nullable=False)
    orchestrator_arn = db.Column(db.String(255))
    worker_arn = db.Column(db.String(255))
    
    # Chunk tracking
    chunks_created = db.Column(db.Integer, default=0)
    chunks_completed = db.Column(db.Integer, default=0)
    chunks_failed = db.Column(db.Integer, default=0)
    chunks_total = db.Column(db.Integer, default=0)
    
    # Progress tracking
    rows_migrated = db.Column(db.BigInteger, default=0)
    rows_total = db.Column(db.BigInteger, default=0)
    progress_percent = db.Column(db.Float, default=0.0)
    
    # Current stage
    current_stage = db.Column(db.String(100), default="initializing")
    
    # Error handling
    error_message = db.Column(db.Text)
    error_details = db.Column(db.JSON)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    migration = db.relationship("MigrationJob", backref="lambda_migration")
    aws_connection = db.relationship("AWSConnection", backref="lambda_migrations")
    chunks = db.relationship("LambdaChunk", backref="lambda_migration", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "migration_id": self.migration_id,
            "aws_connection_id": self.aws_connection_id,
            "status": self.status.value if self.status else None,
            "orchestrator_arn": self.orchestrator_arn,
            "worker_arn": self.worker_arn,
            "chunks_created": self.chunks_created,
            "chunks_completed": self.chunks_completed,
            "chunks_failed": self.chunks_failed,
            "chunks_total": self.chunks_total,
            "rows_migrated": self.rows_migrated,
            "rows_total": self.rows_total,
            "progress_percent": self.progress_percent,
            "current_stage": self.current_stage,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class LambdaChunk(db.Model):
    """Model for tracking individual migration chunks."""
    
    __tablename__ = "lambda_chunks"
    
    id = db.Column(db.Integer, primary_key=True)
    lambda_migration_id = db.Column(db.Integer, db.ForeignKey("lambda_migrations.id"), nullable=False)
    
    # Chunk identification
    chunk_id = db.Column(db.String(255), nullable=False, unique=True)
    table_name = db.Column(db.String(255), nullable=False)
    
    # Row range
    start_row = db.Column(db.BigInteger, default=0)
    end_row = db.Column(db.BigInteger, default=0)
    estimated_rows = db.Column(db.BigInteger, default=0)
    
    # Execution status
    status = db.Column(db.String(50), default="PENDING")
    retry_count = db.Column(db.Integer, default=0)
    
    # Results
    rows_migrated = db.Column(db.BigInteger, default=0)
    rows_failed = db.Column(db.BigInteger, default=0)
    
    # Error handling
    error_message = db.Column(db.Text)
    error_details = db.Column(db.JSON)
    
    # Lambda invocation details
    lambda_request_id = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "lambda_migration_id": self.lambda_migration_id,
            "chunk_id": self.chunk_id,
            "table_name": self.table_name,
            "start_row": self.start_row,
            "end_row": self.end_row,
            "estimated_rows": self.estimated_rows,
            "status": self.status,
            "retry_count": self.retry_count,
            "rows_migrated": self.rows_migrated,
            "rows_failed": self.rows_failed,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "lambda_request_id": self.lambda_request_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
