"""Database Validation Service — orchestrates the full validation pipeline.

Provides two flows:
  - Source validation: credentials -> DB exists -> SELECT -> discover tables -> sample rows
  - Destination validation: credentials -> DB exists -> CREATE TABLE -> INSERT -> SELECT

All connections are closed after validation. Never logs passwords or connection strings.
"""

from __future__ import annotations

import logging
import socket
from typing import Any

from app.schemas.database_validation import (
    DestinationValidationResponse,
    SourceValidationResponse,
    ValidationCheck,
)
from app.services.validators import get_validator
from app.services.validators.sensitive_masker import mask_row, should_mask_column

logger = logging.getLogger(__name__)


class DatabaseValidationError(ValueError):
    """Raised when validation fails at any step."""


class DatabaseValidationService:
    """Orchestrates deep database validation for source and destination endpoints."""

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch to source or destination validation based on purpose."""
        purpose = (payload.get("purpose") or "SOURCE").strip().upper()
        engine = payload.get("database_type", "").strip().upper()
        host = payload.get("host", "").strip()
        port = payload.get("port")
        username = payload.get("username", "").strip()
        password = payload.get("password", "")
        database_name = (payload.get("database_name") or "").strip() or None

        if not host:
            raise DatabaseValidationError("Host is required.")
        if not isinstance(port, int) or port < 1:
            raise DatabaseValidationError("Port must be a positive integer.")
        if not username:
            raise DatabaseValidationError("Username is required.")
        if not password:
            raise DatabaseValidationError("Password is required.")
        if not engine:
            raise DatabaseValidationError("Database type is required.")

        if purpose == "SOURCE":
            return self._validate_source(engine, host, port, username, password, database_name).to_dict()
        else:
            return self._validate_destination(engine, host, port, username, password, database_name).to_dict()

    # ── Source validation ──────────────────────────────────────────────────
    def _validate_source(
        self,
        engine: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database_name: str | None,
    ) -> SourceValidationResponse:
        checks: list[ValidationCheck] = []

        # Step 1: TCP connectivity
        tcp_ok = self._test_tcp(host, port)
        checks.append(ValidationCheck(
            step="connecting",
            label="Host Reachable",
            passed=tcp_ok,
            detail=None if tcp_ok else f"Cannot reach {host}:{port}",
        ))
        if not tcp_ok:
            return SourceValidationResponse(
                connection="failed",
                database=database_name or "",
                checks=checks,
            )

        # Steps 2-9: Database validation
        validator = get_validator(engine, host, port, username, password, database_name)
        try:
            validator.connect()
        except Exception as exc:
            checks.append(ValidationCheck(
                step="authenticating",
                label="Authentication Passed",
                passed=False,
                detail=f"Connection failed: {exc}",
            ))
            return SourceValidationResponse(
                connection="failed",
                database=database_name or "",
                checks=checks,
            )

        try:
            # Step 2: Validate credentials
            try:
                validator.validate_connection()
                checks.append(ValidationCheck(
                    step="authenticating",
                    label="Authentication Passed",
                    passed=True,
                ))
            except Exception as exc:
                checks.append(ValidationCheck(
                    step="authenticating",
                    label="Authentication Passed",
                    passed=False,
                    detail=str(exc),
                ))
                return SourceValidationResponse(
                    connection="failed",
                    database=database_name or "",
                    checks=checks,
                )

            # Step 3: Database exists
            db_exists = validator.database_exists()
            checks.append(ValidationCheck(
                step="database_exists",
                label="Database Found",
                passed=db_exists,
                detail=None if db_exists else f"Database '{database_name}' not found",
            ))
            if not db_exists:
                return SourceValidationResponse(
                    connection="failed",
                    database=database_name or "",
                    checks=checks,
                )

            # Step 4: Check SELECT permission
            perms = validator.validate_permissions()
            has_select = perms.get("SELECT", False)
            checks.append(ValidationCheck(
                step="checking_permissions",
                label="Read Permission Verified",
                passed=has_select,
                detail=None if has_select else "User lacks SELECT privilege",
            ))

            # Step 5: Discover tables
            tables = validator.discover_tables()

            # Step 6: Pick first table and fetch metadata
            selected_table = tables[0] if tables else None
            columns: list[str] = []
            sample_rows: list[dict[str, Any]] = []
            row_count: int | None = None
            masked_columns: list[str] = []

            if selected_table:
                # Step 7: Row count
                row_count = validator.get_table_row_count(selected_table)

                # Step 8: Fetch sample rows (raw from validator)
                columns, raw_rows = validator.fetch_sample_rows(selected_table, limit=5)

                # Step 9: Apply sensitive data masking
                sample_rows = []
                masked_columns_set: set[str] = set()
                for raw_row in raw_rows:
                    masked_row_data, masked_cols = mask_row(raw_row)
                    sample_rows.append(masked_row_data)
                    masked_columns_set.update(masked_cols)

                masked_columns = sorted(masked_columns_set)

            return SourceValidationResponse(
                connection="success",
                database=database_name or "",
                selected_table=selected_table,
                columns=columns,
                sample_rows=sample_rows,
                row_count=row_count,
                tables=tables,
                checks=checks,
                masked_columns=masked_columns,
            )

        finally:
            validator.close()

    # ── Destination validation ─────────────────────────────────────────────
    def _validate_destination(
        self,
        engine: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database_name: str | None,
    ) -> DestinationValidationResponse:
        checks: list[ValidationCheck] = []

        # Step 1: TCP connectivity
        tcp_ok = self._test_tcp(host, port)
        checks.append(ValidationCheck(
            step="connecting",
            label="Host Reachable",
            passed=tcp_ok,
            detail=None if tcp_ok else f"Cannot reach {host}:{port}",
        ))
        if not tcp_ok:
            return DestinationValidationResponse(
                connection="failed",
                database_exists=False,
                write_permission=False,
                read_permission=False,
                checks=checks,
            )

        # Steps 2-6: Database validation
        validator = get_validator(engine, host, port, username, password, database_name)
        try:
            validator.connect()
        except Exception as exc:
            checks.append(ValidationCheck(
                step="authenticating",
                label="Authentication Passed",
                passed=False,
                detail=f"Connection failed: {exc}",
            ))
            return DestinationValidationResponse(
                connection="failed",
                database_exists=False,
                write_permission=False,
                read_permission=False,
                checks=checks,
            )

        try:
            # Step 2: Validate credentials
            try:
                validator.validate_connection()
                checks.append(ValidationCheck(
                    step="authenticating",
                    label="Authentication Passed",
                    passed=True,
                ))
            except Exception as exc:
                checks.append(ValidationCheck(
                    step="authenticating",
                    label="Authentication Passed",
                    passed=False,
                    detail=str(exc),
                ))
                return DestinationValidationResponse(
                    connection="failed",
                    database_exists=False,
                    write_permission=False,
                    read_permission=False,
                    checks=checks,
                )

            # Step 3: Database exists
            db_exists = validator.database_exists()
            checks.append(ValidationCheck(
                step="database_exists",
                label="Database Exists",
                passed=db_exists,
                detail=None if db_exists else f"Database '{database_name}' not found",
            ))

            # Step 4: Check permissions
            perms = validator.validate_permissions()
            has_select = perms.get("SELECT", False)
            has_insert = perms.get("INSERT", False)
            has_create = perms.get("CREATE", False)

            checks.append(ValidationCheck(
                step="read_permission",
                label="Read Permission",
                passed=has_select,
                detail=None if has_select else "User lacks SELECT privilege",
            ))
            checks.append(ValidationCheck(
                step="write_permission",
                label="Write Permission",
                passed=has_insert and has_create,
                detail=None if (has_insert and has_create) else "User lacks INSERT or CREATE TABLE privilege",
            ))

            return DestinationValidationResponse(
                connection="success",
                database_exists=db_exists,
                write_permission=has_insert and has_create,
                read_permission=has_select,
                checks=checks,
            )

        finally:
            validator.close()

    # ── Helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _test_tcp(host: str, port: int, timeout: int = 5) -> bool:
        """Test TCP socket reachability."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, socket.error, OSError):
            return False
