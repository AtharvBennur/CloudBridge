"""
Purpose:
This file defines the SQLAlchemy model for AWS account connections.

Why:
The backend needs a persistent representation for customer AWS account metadata that can be created, listed, updated, and deleted.

Architecture:
Flask Application Factory
↓
SQLAlchemy Model
↓
AWS Connection Service
↓
AWS Connection Routes
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import text

from app.extensions import db


class AWSConnectionStatus:
    """Centralizes the supported AWS connection status values."""

    PENDING = "PENDING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    FAILED = "FAILED"

    VALUES = {PENDING, CONNECTED, DISCONNECTED, FAILED}


class AWSConnection(db.Model):
    """Represents a customer AWS account connection and its metadata."""

    __tablename__ = "aws_connections"

    id = db.Column(db.Integer, primary_key=True)
    aws_account_id = db.Column(db.String(64), nullable=False, index=True)
    aws_region = db.Column(db.String(64), nullable=False)
    role_arn = db.Column(db.String(512), nullable=True)
    external_id = db.Column(db.String(64), nullable=False, unique=True, default=lambda: str(uuid4()))
    connection_status = db.Column(db.String(32), nullable=False, default=AWSConnectionStatus.PENDING)
    last_validated_at = db.Column(db.DateTime, nullable=True)
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
        return f"AWSConnection(id={self.id}, aws_account_id={self.aws_account_id!r})"
