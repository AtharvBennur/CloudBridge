"""Database Validation Service — orchestrates the full validation pipeline.

Provides two flows:
  - Source validation: credentials -> DB exists -> SELECT -> discover tables -> sample rows
  - Destination validation: credentials -> DB exists -> CREATE TABLE -> INSERT -> SELECT

All connections are closed after validation. Never logs passwords or connection strings.

Production-grade implementation with:
  - No redundant TCP checks (pymysql handles TCP + handshake + auth)
  - Detailed logging at each step
  - Full exception tracebacks
  - Proper error messages
"""

from __future__ import annotations

import logging
import traceback
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

        logger.info(
            "Database validation started",
            extra={
                "database_type": engine,
                "host": host,
                "port": port,
                "purpose": purpose,
                "database_name": database_name or "(none)",
            }
        )

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
        """Validate source database connection with comprehensive checks.
        
        Validation steps:
        1. Connect (TCP + MySQL handshake + authentication)
        2. SELECT 1 (verify connection works)
        3. Database exists
        4. Check permissions
        5. Discover tables
        6. Fetch sample rows
        """
        checks: list[ValidationCheck] = []
        logger.info(
            "Starting SOURCE validation",
            extra={
                "host": host,
                "port": port,
                "database_name": database_name or "(none)",
                "purpose": "SOURCE",
            }
        )

        # Step 1: Connect to database (TCP + handshake + auth all in one)
        validator = get_validator(engine, host, port, username, password, database_name, timeout=300)
        try:
            logger.debug("Step 1: Connecting to database...")
            validator.connect()
            logger.info("✓ Step 1: Connection successful")
            
            # Step 2: Validate connection with SELECT 1
            logger.debug("Step 2: Executing SELECT 1...")
            validator.validate_connection()
            checks.append(ValidationCheck(
                step="authenticating",
                label="Authentication Passed",
                passed=True,
            ))
            logger.info("✓ Step 2: SELECT 1 successful")
            
        except Exception as exc:
            # Connection failed - this includes TCP, handshake, AND authentication
            error_detail = _format_validation_error(exc, host, port, username, database_name)
            logger.error("✗ Connection failed: %s", error_detail)
            logger.error("Full traceback:\n%s", traceback.format_exc())
            
            checks.append(ValidationCheck(
                step="connecting",
                label="Connection Failed",
                passed=False,
                detail=error_detail,
            ))
            
            return SourceValidationResponse(
                connection="failed",
                database=database_name or "",
                checks=checks,
            )

        try:
            # Step 3: Database exists
            logger.debug("Step 3: Checking if database '%s' exists...", database_name)
            try:
                db_exists = validator.database_exists()
            except Exception as exc:
                logger.error("✗ Database existence check failed: %s", exc)
                checks.append(ValidationCheck(
                    step="database_exists",
                    label="Database Found",
                    passed=False,
                    detail=f"Unable to verify database '{database_name}': {exc}",
                ))
                return SourceValidationResponse(
                    connection="failed",
                    database=database_name or "",
                    checks=checks,
                )

            checks.append(ValidationCheck(
                step="database_exists",
                label="Database Found",
                passed=db_exists,
                detail=None if db_exists else f"Database '{database_name}' not found",
            ))
            logger.info("✓ Step 3: Database exists: %s", db_exists)
            
            if not db_exists:
                return SourceValidationResponse(
                    connection="failed",
                    database=database_name or "",
                    checks=checks,
                )

            # Step 4: Check SELECT permission
            logger.debug("Step 4: Validating permissions...")
            try:
                perms = validator.validate_permissions()
            except Exception as exc:
                logger.error("✗ Permission validation failed: %s", exc)
                checks.append(ValidationCheck(
                    step="checking_permissions",
                    label="Read Permission Verified",
                    passed=False,
                    detail=f"Unable to verify permissions: {exc}",
                ))
                return SourceValidationResponse(
                    connection="failed",
                    database=database_name or "",
                    checks=checks,
                )

            has_select = perms.get("SELECT", False)
            checks.append(ValidationCheck(
                step="checking_permissions",
                label="Read Permission Verified",
                passed=has_select,
                detail=None if has_select else "User lacks SELECT privilege",
            ))
            logger.info("✓ Step 4: SELECT permission: %s", has_select)
            
            if not has_select:
                return SourceValidationResponse(
                    connection="failed",
                    database=database_name or "",
                    checks=checks,
                )

            # Step 5: Discover tables
            logger.debug("Step 5: Discovering tables...")
            try:
                tables = validator.discover_tables()
            except Exception as exc:
                logger.error("✗ Table discovery failed: %s", exc)
                checks.append(ValidationCheck(
                    step="discovering_tables",
                    label="Table Discovery",
                    passed=False,
                    detail=f"Unable to discover tables: {exc}",
                ))
                return SourceValidationResponse(
                    connection="failed",
                    database=database_name or "",
                    checks=checks,
                )

            checks.append(ValidationCheck(
                step="discovering_tables",
                label="Table Discovery",
                passed=True,
                detail=f"Found {len(tables)} table(s)",
            ))
            logger.info("✓ Step 5: Discovered %d tables", len(tables))

            # Step 5.5: Execute verification query to ensure genuine connection
            logger.debug("Step 5.5: Executing verification query...")
            try:
                validator.execute_verify_query()
                checks.append(ValidationCheck(
                    step="verify_query",
                    label="Verification Query Executed",
                    passed=True,
                    detail="Successfully executed verification query",
                ))
                logger.info("✓ Step 5.5: Verification query successful")
            except Exception as exc:
                logger.error("✗ Verification query failed: %s", exc)
                checks.append(ValidationCheck(
                    step="verify_query",
                    label="Verification Query Executed",
                    passed=False,
                    detail=f"Unable to execute verification query: {exc}",
                ))
                return SourceValidationResponse(
                    connection="failed",
                    database=database_name or "",
                    checks=checks,
                )

            # Step 6: Pick first table and fetch metadata
            selected_table = tables[0] if tables else None
            columns: list[str] = []
            sample_rows: list[dict[str, Any]] = []
            row_count: int | None = None
            masked_columns: list[str] = []

            if selected_table:
                logger.debug("Step 6: Fetching sample rows from '%s'...", selected_table)
                try:
                    # Step 7: Row count
                    row_count = validator.get_table_row_count(selected_table)

                    # Step 8: Fetch sample rows (raw from validator)
                    columns, raw_rows = validator.fetch_sample_rows(selected_table, limit=5)
                    logger.info("✓ Step 6: Fetched %d rows from '%s'", len(raw_rows), selected_table)
                except Exception as exc:
                    logger.error("✗ Table preview failed: %s", exc)
                    checks.append(ValidationCheck(
                        step="previewing_table",
                        label="Table Preview",
                        passed=False,
                        detail=f"Connected successfully, but unable to preview table '{selected_table}': {exc}",
                    ))
                    return SourceValidationResponse(
                        connection="failed",
                        database=database_name or "",
                        selected_table=selected_table,
                        tables=tables,
                        checks=checks,
                    )

                # Step 9: Apply sensitive data masking
                sample_rows = []
                masked_columns_set: set[str] = set()
                for raw_row in raw_rows:
                    masked_row_data, masked_cols = mask_row(raw_row)
                    sample_rows.append(masked_row_data)
                    masked_columns_set.update(masked_cols)

                masked_columns = sorted(masked_columns_set)
                checks.append(ValidationCheck(
                    step="previewing_table",
                    label="Table Preview",
                    passed=True,
                    detail=f"Previewed table '{selected_table}'",
                ))

            logger.info("✓ SOURCE validation completed successfully")
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
            logger.debug("Closing database connection")
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
        """Validate destination database connection with comprehensive checks.
        
        Validation steps:
        1. Connect (TCP + MySQL handshake + authentication)
        2. SELECT 1 (verify connection works)
        3. Database exists
        4. Check permissions (SELECT, INSERT, CREATE)
        """
        checks: list[ValidationCheck] = []
        logger.info("Starting DESTINATION validation for %s:%s/%s", host, port, database_name or "(none)")

        # Step 1: Connect to database (TCP + handshake + auth all in one)
        validator = get_validator(engine, host, port, username, password, database_name, timeout=300)
        try:
            logger.debug("Step 1: Connecting to database...")
            validator.connect()
            logger.info("✓ Step 1: Connection successful")
            
            # Step 2: Validate connection with SELECT 1
            logger.debug("Step 2: Executing SELECT 1...")
            validator.validate_connection()
            checks.append(ValidationCheck(
                step="authenticating",
                label="Authentication Passed",
                passed=True,
            ))
            logger.info("✓ Step 2: SELECT 1 successful")
            
        except Exception as exc:
            # Connection failed - this includes TCP, handshake, AND authentication
            error_detail = _format_validation_error(exc, host, port, username, database_name)
            logger.error("✗ Connection failed: %s", error_detail)
            logger.error("Full traceback:\n%s", traceback.format_exc())
            
            checks.append(ValidationCheck(
                step="connecting",
                label="Connection Failed",
                passed=False,
                detail=error_detail,
            ))
            
            return DestinationValidationResponse(
                connection="failed",
                database_exists=False,
                write_permission=False,
                read_permission=False,
                checks=checks,
            )

        try:
            # Step 3: Database exists
            logger.debug("Step 3: Checking if database '%s' exists...", database_name)
            try:
                db_exists = validator.database_exists()
            except Exception as exc:
                logger.error("✗ Database existence check failed: %s", exc)
                checks.append(ValidationCheck(
                    step="database_exists",
                    label="Database Exists",
                    passed=False,
                    detail=f"Unable to verify database '{database_name}': {exc}",
                ))
                return DestinationValidationResponse(
                    connection="failed",
                    database_exists=False,
                    write_permission=False,
                    read_permission=False,
                    checks=checks,
                )

            checks.append(ValidationCheck(
                step="database_exists",
                label="Database Exists",
                passed=db_exists,
                detail=None if db_exists else f"Database '{database_name}' not found",
            ))
            logger.info("✓ Step 3: Database exists: %s", db_exists)
            
            if not db_exists:
                return DestinationValidationResponse(
                    connection="failed",
                    database_exists=False,
                    write_permission=False,
                    read_permission=False,
                    checks=checks,
                )

            # Step 4: Check permissions
            logger.debug("Step 4: Validating permissions...")
            try:
                perms = validator.validate_permissions()
            except Exception as exc:
                logger.error("✗ Permission validation failed: %s", exc)
                checks.append(ValidationCheck(
                    step="checking_permissions",
                    label="Permissions Verified",
                    passed=False,
                    detail=f"Unable to verify permissions: {exc}",
                ))
                return DestinationValidationResponse(
                    connection="failed",
                    database_exists=True,
                    write_permission=False,
                    read_permission=False,
                    checks=checks,
                )

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
            
            logger.info("✓ Step 4: Permissions validated: SELECT=%s INSERT=%s CREATE=%s",
                       has_select, has_insert, has_create)

            # Step 5: Execute SHOW TABLES to verify database accessibility
            logger.debug("Step 5: Executing SHOW TABLES to verify database accessibility...")
            try:
                tables = validator.discover_tables()
                checks.append(ValidationCheck(
                    step="table_accessibility",
                    label="Table Accessibility Verified",
                    passed=True,
                    detail=f"Successfully executed SHOW TABLES, found {len(tables)} tables",
                ))
                logger.info("✓ Step 5: SHOW TABLES successful, found %d tables", len(tables))
            except Exception as exc:
                logger.error("✗ SHOW TABLES failed: %s", exc)
                checks.append(ValidationCheck(
                    step="table_accessibility",
                    label="Table Accessibility Verified",
                    passed=False,
                    detail=f"Unable to execute SHOW TABLES: {exc}",
                ))
                return DestinationValidationResponse(
                    connection="failed",
                    database_exists=True,
                    write_permission=False,
                    read_permission=False,
                    checks=checks,
                )

            # Step 6: Execute additional verification query
            logger.debug("Step 6: Executing additional verification query...")
            try:
                validator.execute_verify_query()
                checks.append(ValidationCheck(
                    step="verify_query",
                    label="Verification Query Executed",
                    passed=True,
                    detail="Successfully executed verification query",
                ))
                logger.info("✓ Step 6: Verification query successful")
            except Exception as exc:
                logger.error("✗ Verification query failed: %s", exc)
                checks.append(ValidationCheck(
                    step="verify_query",
                    label="Verification Query Executed",
                    passed=False,
                    detail=f"Unable to execute verification query: {exc}",
                ))
                return DestinationValidationResponse(
                    connection="failed",
                    database_exists=True,
                    write_permission=False,
                    read_permission=False,
                    checks=checks,
                )

            logger.info("✓ DESTINATION validation completed successfully")
            return DestinationValidationResponse(
                connection="success",
                database_exists=db_exists,
                write_permission=has_insert and has_create,
                read_permission=has_select,
                checks=checks,
            )

        finally:
            logger.debug("Closing database connection")
            validator.close()


def _format_validation_error(exc: Exception, host: str, port: int, username: str, database_name: str | None) -> str:
    """Format PyMySQL and network errors with Problem, Cause, and Suggested Fix."""
    err_str = str(exc)
    err_lower = err_str.lower()
    
    if "10060" in err_str or "2003" in err_str or "timed out" in err_lower:
        return (
            f"Problem: TCP Connection Timeout to {host}:{port}.\n"
            f"Cause: The target database server is unreachable over TCP port {port}. (Details: {err_str})\n"
            f"Suggested Fix:\n"
            f"  1. Ensure AWS RDS/EC2 Security Group permits inbound traffic on port {port} from 0.0.0.0/0 or your backend server IP.\n"
            f"  2. Verify that AWS RDS 'Publicly Accessible' setting is set to 'Yes' if connecting over the internet.\n"
            f"  3. Check that the RDS instance status is 'Available'."
        )
    elif "1045" in err_str or "access denied" in err_lower:
        return (
            f"Problem: Authentication failed for user '{username}'.\n"
            f"Cause: Invalid password or user host privileges restriction on MySQL server. (Details: {err_str})\n"
            f"Suggested Fix: Verify database credentials in AWS Secrets Manager or payload form. Ensure user '{username}' has remote connect grants."
        )
    elif "1049" in err_str or "unknown database" in err_lower:
        return (
            f"Problem: Database '{database_name}' does not exist.\n"
            f"Cause: Target MySQL server has no database named '{database_name}'. (Details: {err_str})\n"
            f"Suggested Fix: Execute 'CREATE DATABASE `{database_name}`;' on the MySQL server or correct the database name."
        )
    else:
        return (
            f"Problem: Database validation error on {host}:{port}.\n"
            f"Cause: {err_str}\n"
            f"Suggested Fix: Check database server logs, network firewall settings, and account permissions."
        )

