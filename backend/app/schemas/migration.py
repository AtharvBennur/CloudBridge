"""
Purpose:
This file defines the request and response schemas for migration endpoints.

Why:
Schemas make the API contract explicit and keep validation logic readable and testable.

Architecture:
Migration Routes
↓
Migration Service
↓
Migration Job Model
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.migration import MigrationJob, MigrationStatus


@dataclass(frozen=True)
class CreateMigrationRequest:
    """Represents the payload required to create a new migration job."""

    job_name: str
    source_database: str
    destination_database: str
    description: str | None = None
    aws_connection_id: int | None = None
    source_database_config_id: int | None = None
    destination_database_config_id: int | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "CreateMigrationRequest":
        """Convert raw JSON into a validated creation request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        job_name = payload.get("job_name")
        source_database = payload.get("source_database")
        destination_database = payload.get("destination_database")
        description = payload.get("description")
        aws_connection_id = payload.get("aws_connection_id")
        source_database_config_id = payload.get("source_database_config_id")
        destination_database_config_id = payload.get("destination_database_config_id")

        if not isinstance(job_name, str) or not job_name.strip():
            raise ValueError("Job name is required.")

        if not isinstance(source_database, str) or not source_database.strip():
            raise ValueError("Source database is required.")

        if not isinstance(destination_database, str) or not destination_database.strip():
            raise ValueError("Destination database is required.")

        if description is not None and not isinstance(description, str):
            raise ValueError("Description must be a string.")

        try:
            if aws_connection_id is not None:
                aws_connection_id = int(aws_connection_id)
            if source_database_config_id is not None:
                source_database_config_id = int(source_database_config_id)
            if destination_database_config_id is not None:
                destination_database_config_id = int(destination_database_config_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Connection and database config IDs must be integers.") from exc

        return cls(
            job_name=job_name.strip(),
            source_database=source_database.strip(),
            destination_database=destination_database.strip(),
            description=description.strip() if isinstance(description, str) else None,
            aws_connection_id=aws_connection_id,
            source_database_config_id=source_database_config_id,
            destination_database_config_id=destination_database_config_id,
        )


@dataclass(frozen=True)
class UpdateMigrationRequest:
    """Represents the payload used to update an existing migration job."""

    job_name: str | None = None
    source_database: str | None = None
    destination_database: str | None = None
    status: str | None = None
    description: str | None = None
    aws_connection_id: int | None = None
    source_database_config_id: int | None = None
    destination_database_config_id: int | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "UpdateMigrationRequest":
        """Convert raw JSON into a validated update request object."""
        if payload is None:
            return cls()

        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        job_name = payload.get("job_name")
        source_database = payload.get("source_database")
        destination_database = payload.get("destination_database")
        status = payload.get("status")
        description = payload.get("description")
        aws_connection_id = payload.get("aws_connection_id")
        source_database_config_id = payload.get("source_database_config_id")
        destination_database_config_id = payload.get("destination_database_config_id")

        if job_name is not None and (not isinstance(job_name, str) or not job_name.strip()):
            raise ValueError("Job name must be a non-empty string.")

        if source_database is not None and (not isinstance(source_database, str) or not source_database.strip()):
            raise ValueError("Source database must be a non-empty string.")

        if destination_database is not None and (not isinstance(destination_database, str) or not destination_database.strip()):
            raise ValueError("Destination database must be a non-empty string.")

        if status is not None:
            if not isinstance(status, str) or not status.strip():
                raise ValueError("Status must be a non-empty string.")
            normalized_status = status.strip().upper()
            if normalized_status not in MigrationStatus.VALUES:
                raise ValueError(
                    "Status must be one of: PENDING, QUEUED, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED."
                )
            status = normalized_status

        if description is not None and not isinstance(description, str):
            raise ValueError("Description must be a string.")

        try:
            if aws_connection_id is not None:
                aws_connection_id = int(aws_connection_id)
            if source_database_config_id is not None:
                source_database_config_id = int(source_database_config_id)
            if destination_database_config_id is not None:
                destination_database_config_id = int(destination_database_config_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Connection and database config IDs must be integers.") from exc

        return cls(
            job_name=job_name.strip() if isinstance(job_name, str) else None,
            source_database=source_database.strip() if isinstance(source_database, str) else None,
            destination_database=destination_database.strip() if isinstance(destination_database, str) else None,
            status=status,
            description=description.strip() if isinstance(description, str) else None,
            aws_connection_id=aws_connection_id,
            source_database_config_id=source_database_config_id,
            destination_database_config_id=destination_database_config_id,
        )


@dataclass(frozen=True)
class MigrationResponse:
    """Represents the structured JSON returned by migration endpoints."""

    id: int
    job_name: str
    source_database: str
    destination_database: str
    status: str
    description: str | None
    aws_connection_id: int | None
    source_database_config_id: int | None
    destination_database_config_id: int | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        return {
            "id": self.id,
            "job_name": self.job_name,
            "source_database": self.source_database,
            "destination_database": self.destination_database,
            "status": self.status,
            "description": self.description,
            "aws_connection_id": self.aws_connection_id,
            "source_database_config_id": self.source_database_config_id,
            "destination_database_config_id": self.destination_database_config_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_model(cls, migration: MigrationJob) -> "MigrationResponse":
        """Build a response DTO from a persisted migration job."""
        return cls(
            id=migration.id,
            job_name=migration.job_name,
            source_database=migration.source_database,
            destination_database=migration.destination_database,
            status=migration.status,
            description=migration.description,
            aws_connection_id=migration.aws_connection_id,
            source_database_config_id=migration.source_database_config_id,
            destination_database_config_id=migration.destination_database_config_id,
            created_at=migration.created_at.isoformat() if migration.created_at else "",
            updated_at=migration.updated_at.isoformat() if migration.updated_at else "",
        )


@dataclass(frozen=True)
class DeleteMigrationResponse:
    """Represents the response returned after a migration delete operation."""

    message: str

    def to_dict(self) -> dict[str, str]:
        """Convert the response object into a JSON-safe dictionary."""
        return {"message": self.message}
