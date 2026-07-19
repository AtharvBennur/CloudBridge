"""Persist database onboarding configuration for source and destination databases."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.extensions import db


class DatabaseConfigType:
    """Supported database kinds for onboarding."""

    POSTGRESQL = "POSTGRESQL"
    MYSQL = "MYSQL"
    ORACLE = "ORACLE"
    SQL_SERVER = "SQL_SERVER"

    VALUES = {POSTGRESQL, MYSQL, ORACLE, SQL_SERVER}


class DatabaseConfig(db.Model):
    """Stores onboarding metadata for a database endpoint."""

    __tablename__ = "database_configs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    database_type = db.Column(db.String(64), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(255), nullable=False)
    database_name = db.Column(db.String(255), nullable=True)  # Actual DB name on the server
    secret_arn = db.Column(db.String(512), nullable=True)
    secret_name = db.Column(db.String(255), nullable=True)
    provisioning_config = db.Column(db.Text, nullable=True)
    purpose = db.Column(db.String(32), nullable=False, default="SOURCE")
    aws_connection_id = db.Column(db.Integer, db.ForeignKey("aws_connections.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return f"DatabaseConfig(id={self.id}, name={self.name!r})"
