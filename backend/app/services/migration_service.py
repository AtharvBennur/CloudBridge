"""
Purpose:
This file contains the migration business logic.

Why:
Routes should remain thin, while the service layer owns validation, persistence, and response shaping.

Architecture:
Migration Routes
↓
Migration Service
↓
SQLAlchemy Model
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import current_app

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.exceptions.migration import (
    MigrationIntegrityError,
    MigrationNotFoundError,
    MigrationValidationError,
)
from app.extensions import db
from app.models.aws_connection import AWSConnection
from app.models.database_config import DatabaseConfig
from app.models.migration import MigrationJob, MigrationStatus
from app.schemas.migration import (
    CreateMigrationRequest,
    DeleteMigrationResponse,
    MigrationResponse,
    UpdateMigrationRequest,
)


class MigrationService:
    """Coordinates migration job CRUD behavior for the current sprint."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def create(self, payload: dict[str, Any] | None) -> MigrationResponse:
        """Validate and persist a new migration job."""
        try:
            create_request = CreateMigrationRequest.from_payload(payload)
        except ValueError as exc:
            raise MigrationValidationError(str(exc)) from exc

        # Validate foreign key references before persisting
        self._validate_foreign_keys(
            aws_connection_id=create_request.aws_connection_id,
            source_database_config_id=create_request.source_database_config_id,
            destination_database_config_id=create_request.destination_database_config_id,
        )

        try:
            migration_job = MigrationJob(
                job_name=create_request.job_name,
                source_database=create_request.source_database,
                destination_database=create_request.destination_database,
                status=MigrationStatus.PENDING,
                description=create_request.description,
                aws_connection_id=create_request.aws_connection_id,
                source_database_config_id=create_request.source_database_config_id,
                destination_database_config_id=create_request.destination_database_config_id,
            )
            db.session.add(migration_job)
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise MigrationIntegrityError(
                f"Referenced resource does not exist: {exc.orig}"
            ) from exc
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise MigrationIntegrityError(
                f"Database error while creating migration: {exc.orig}"
            ) from exc

        self._log_info("Migration created", migration_job.id, migration_job.job_name)
        return MigrationResponse.from_model(migration_job)

    def list(self) -> list[MigrationResponse]:
        """Return all migration jobs in descending creation order."""
        migration_jobs = MigrationJob.query.order_by(MigrationJob.created_at.desc()).all()
        self._log_info("Migration jobs retrieved")
        return [MigrationResponse.from_model(job) for job in migration_jobs]

    def get(self, migration_id: int) -> MigrationResponse:
        """Return a single migration job by ID."""
        migration_job = self._get_existing_migration(migration_id)
        self._log_info("Migration retrieved", migration_job.id, migration_job.job_name)
        return MigrationResponse.from_model(migration_job)

    def update(self, migration_id: int, payload: dict[str, Any] | None) -> MigrationResponse:
        """Update an existing migration job and persist the changes."""
        migration_job = self._get_existing_migration(migration_id)

        try:
            update_request = UpdateMigrationRequest.from_payload(payload)
        except ValueError as exc:
            raise MigrationValidationError(str(exc)) from exc

        # Validate foreign key references if they are being changed
        self._validate_foreign_keys(
            aws_connection_id=update_request.aws_connection_id,
            source_database_config_id=update_request.source_database_config_id,
            destination_database_config_id=update_request.destination_database_config_id,
        )

        try:
            if update_request.job_name is not None:
                migration_job.job_name = update_request.job_name
            if update_request.source_database is not None:
                migration_job.source_database = update_request.source_database
            if update_request.destination_database is not None:
                migration_job.destination_database = update_request.destination_database
            if update_request.status is not None:
                migration_job.status = update_request.status
            if update_request.description is not None:
                migration_job.description = update_request.description
            if update_request.aws_connection_id is not None:
                migration_job.aws_connection_id = update_request.aws_connection_id
            if update_request.source_database_config_id is not None:
                migration_job.source_database_config_id = update_request.source_database_config_id
            if update_request.destination_database_config_id is not None:
                migration_job.destination_database_config_id = update_request.destination_database_config_id

            migration_job.updated_at = datetime.utcnow()
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise MigrationIntegrityError(
                f"Referenced resource does not exist: {exc.orig}"
            ) from exc
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise MigrationIntegrityError(
                f"Database error while updating migration: {exc.orig}"
            ) from exc

        self._log_info("Migration updated", migration_job.id, migration_job.job_name)
        return MigrationResponse.from_model(migration_job)

    def delete(self, migration_id: int) -> DeleteMigrationResponse:
        """Delete a migration job from the data store."""
        migration_job = self._get_existing_migration(migration_id)
        db.session.delete(migration_job)
        db.session.commit()
        self._log_info("Migration deleted", migration_job.id, migration_job.job_name)
        return DeleteMigrationResponse(message="Migration job deleted successfully.")

    def _get_existing_migration(self, migration_id: int) -> MigrationJob:
        """Return an existing migration job or raise a not-found error."""
        migration_job = MigrationJob.query.get(migration_id)
        if migration_job is None:
            raise MigrationNotFoundError(f"Migration job {migration_id} was not found.")
        return migration_job

    @staticmethod
    def _validate_foreign_keys(
        aws_connection_id: int | None = None,
        source_database_config_id: int | None = None,
        destination_database_config_id: int | None = None,
    ) -> None:
        """Verify that referenced foreign keys exist before persisting."""
        if aws_connection_id is not None:
            if not AWSConnection.query.get(aws_connection_id):
                raise MigrationIntegrityError(
                    f"AWS connection with id {aws_connection_id} does not exist."
                )
        if source_database_config_id is not None:
            if not DatabaseConfig.query.get(source_database_config_id):
                raise MigrationIntegrityError(
                    f"Source database config with id {source_database_config_id} does not exist."
                )
        if destination_database_config_id is not None:
            if not DatabaseConfig.query.get(destination_database_config_id):
                raise MigrationIntegrityError(
                    f"Destination database config with id {destination_database_config_id} does not exist."
                )

    def _log_info(self, message: str, migration_id: int | None = None, job_name: str | None = None) -> None:
        """Write a structured log entry through Flask's configured logger."""
        logger = self._logger or current_app.logger
        if migration_id is not None and job_name is not None:
            logger.info("%s for migration %s (%s)", message, migration_id, job_name)
            return
        logger.info(message)
