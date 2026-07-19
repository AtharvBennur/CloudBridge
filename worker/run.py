"""
CloudBridge ECS Migration Worker

Runs inside an AWS Fargate container. Performs the actual database migration:
1. Fetches migration configuration from the CloudBridge API
2. Resolves database credentials (from Secrets Manager or direct config)
3. Connects to source and destination databases
4. Discovers tables and creates missing ones on destination
5. Copies data in batches with progress reporting
6. Updates migration status on completion or failure

Environment variables (set by ECS task definition overrides):
- CLOUDBRIDGE_API_URL: Base URL of the CloudBridge backend
- MIGRATION_ID: ID of the migration job to execute
- AWS_CONNECTION_ID: ID of the AWS connection (for Secrets Manager access)
- SOURCE_DB_CONFIG_ID: (optional) ID of source database config
- DESTINATION_DB_CONFIG_ID: (optional) ID of destination database config
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any

import boto3
import psycopg2
import requests
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("migration-worker")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_URL = os.environ.get("CLOUDBRIDGE_API_URL", "").rstrip("/")
MIGRATION_ID = os.environ.get("MIGRATION_ID", "")
AWS_CONNECTION_ID = os.environ.get("AWS_CONNECTION_ID", "")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# Source DB credentials (passed as env vars by ECS task)
SOURCE_DB_HOST = os.environ.get("SOURCE_DB_HOST", "")
SOURCE_DB_PORT = int(os.environ.get("SOURCE_DB_PORT", "5432"))
SOURCE_DB_USERNAME = os.environ.get("SOURCE_DB_USERNAME", "")
SOURCE_DB_NAME = os.environ.get("SOURCE_DB_NAME", "")
SOURCE_DB_SECRET_ARN = os.environ.get("SOURCE_DB_SECRET_ARN", "")

# Destination DB credentials (passed as env vars by ECS task)
DEST_DB_HOST = os.environ.get("DEST_DB_HOST", "")
DEST_DB_PORT = int(os.environ.get("DEST_DB_PORT", "5432"))
DEST_DB_USERNAME = os.environ.get("DEST_DB_USERNAME", "")
DEST_DB_NAME = os.environ.get("DEST_DB_NAME", "")
DEST_DB_SECRET_ARN = os.environ.get("DEST_DB_SECRET_ARN", "")

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "5000"))
PROGRESS_REPORT_INTERVAL = int(os.environ.get("PROGRESS_REPORT_INTERVAL", "5000"))

# ---------------------------------------------------------------------------
# CloudBridge API client
# ---------------------------------------------------------------------------


def api_get(path: str) -> dict[str, Any]:
    resp = requests.get(f"{API_URL}{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    resp = requests.post(f"{API_URL}{path}", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Database credential resolution
# ---------------------------------------------------------------------------


def resolve_secret_credentials(secret_arn: str, region: str) -> dict[str, str]:
    """Retrieve database credentials from AWS Secrets Manager."""
    logger.info("Retrieving credentials from Secrets Manager: %s", secret_arn)
    sm_client = boto3.client("secretsmanager", region_name=region)
    try:
        response = sm_client.get_secret_value(SecretId=secret_arn)
        return json.loads(response.get("SecretString", "{}"))
    except ClientError as exc:
        raise RuntimeError(f"Failed to retrieve secret {secret_arn}: {exc}") from exc


def get_source_credentials() -> dict[str, Any]:
    """Build source database connection parameters."""
    if SOURCE_DB_SECRET_ARN:
        secret = resolve_secret_credentials(SOURCE_DB_SECRET_ARN, AWS_REGION)
        return {
            "host": SOURCE_DB_HOST,
            "port": SOURCE_DB_PORT,
            "username": secret.get("username", SOURCE_DB_USERNAME),
            "password": secret.get("password", ""),
            "database": secret.get("dbname", SOURCE_DB_NAME),
        }
    return {
        "host": SOURCE_DB_HOST,
        "port": SOURCE_DB_PORT,
        "username": SOURCE_DB_USERNAME,
        "password": os.environ.get("SOURCE_DB_PASSWORD", ""),
        "database": SOURCE_DB_NAME,
    }


def get_destination_credentials() -> dict[str, Any]:
    """Build destination database connection parameters."""
    if DEST_DB_SECRET_ARN:
        secret = resolve_secret_credentials(DEST_DB_SECRET_ARN, AWS_REGION)
        return {
            "host": DEST_DB_HOST,
            "port": DEST_DB_PORT,
            "username": secret.get("username", DEST_DB_USERNAME),
            "password": secret.get("password", ""),
            "database": secret.get("dbname", DEST_DB_NAME),
        }
    return {
        "host": DEST_DB_HOST,
        "port": DEST_DB_PORT,
        "username": DEST_DB_USERNAME,
        "password": os.environ.get("DEST_DB_PASSWORD", ""),
        "database": DEST_DB_NAME,
    }


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------


def get_connection_string(creds: dict[str, Any]) -> str:
    return (
        f"host={creds['host']} port={creds['port']} "
        f"dbname={creds['database']} user={creds['username']} "
        f"password={creds['password']} sslmode=require connect_timeout=10"
    )


def discover_tables(conn) -> list[str]:
    """Return list of user tables in the source database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        return [row[0] for row in cur.fetchall()]


def get_table_row_count(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        return cur.fetchone()[0]


def get_table_columns(conn, table: str) -> list[tuple[str, str]]:
    """Return list of (column_name, data_type) for a table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return cur.fetchall()


def create_table_if_not_exists(dest_conn, src_conn, table: str) -> None:
    """Create the table on destination if it doesn't exist, matching source schema."""
    with dest_conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            )
            """,
            (table,),
        )
        exists = cur.fetchone()[0]

    if exists:
        logger.info("Table '%s' already exists on destination", table)
        return

    columns = get_table_columns(src_conn, table)
    if not columns:
        logger.warning("Table '%s' has no columns, skipping", table)
        return

    col_defs = ", ".join(f'"{name}" {dtype.upper()}' for name, dtype in columns)
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({col_defs})'

    with dest_conn.cursor() as cur:
        cur.execute(create_sql)
    dest_conn.commit()
    logger.info("Created table '%s' on destination", table)


def copy_table_in_batches(
    src_conn,
    dest_conn,
    table: str,
    migration_id: int,
    total_rows: int,
    rows_already_migrated: int,
) -> int:
    """Copy rows from source to destination in batches. Returns rows copied."""
    columns = get_table_columns(src_conn, table)
    col_names = [c[0] for c in columns]
    col_list = ", ".join(f'"{c}"' for c in col_names)
    placeholders = ", ".join(["%s"] * len(col_names))

    rows_copied = 0
    offset = rows_already_migrated

    while True:
        with src_conn.cursor() as cur:
            cur.execute(
                f'SELECT {col_list} FROM "{table}" LIMIT %s OFFSET %s',
                (BATCH_SIZE, offset),
            )
            rows = cur.fetchall()

        if not rows:
            break

        with dest_conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
                    row,
                )
        dest_conn.commit()

        rows_copied += len(rows)
        offset += len(rows)
        total_copied = rows_already_migrated + rows_copied

        # Report progress
        if total_rows > 0:
            progress = min((total_copied / total_rows) * 100.0, 100.0)
        else:
            progress = 100.0

        logger.info(
            "Table '%s': copied %d rows (total: %d, progress: %.1f%%)",
            table,
            rows_copied,
            total_copied,
            progress,
        )

        # Update CloudBridge with progress
        try:
            api_post(
                "/migration-engine/checkpoint",
                {
                    "migration_id": migration_id,
                    "checkpoint_name": f"batch_{table}_{total_copied}",
                    "progress_percent": round(progress, 2),
                    "rows_processed": total_copied,
                    "metadata": json.dumps({"table": table, "rows_copied": rows_copied}),
                },
            )
        except requests.RequestException as exc:
            logger.warning("Failed to report progress: %s", exc)

    return rows_copied


# ---------------------------------------------------------------------------
# Main migration logic
# ---------------------------------------------------------------------------


def run_migration() -> None:
    if not API_URL:
        logger.error("CLOUDBRIDGE_API_URL is not set")
        sys.exit(1)
    if not MIGRATION_ID:
        logger.error("MIGRATION_ID is not set")
        sys.exit(1)

    migration_id = int(MIGRATION_ID)
    logger.info("Starting migration %d", migration_id)

    # 1. Fetch migration details
    try:
        migration = api_get(f"/migrations/{migration_id}")
    except requests.RequestException as exc:
        logger.error("Failed to fetch migration: %s", exc)
        api_post(
            "/migration-engine/status-update",
            {"migration_id": migration_id, "status": "FAILED", "error": str(exc)},
        )
        sys.exit(1)

    logger.info("Migration: %s (%s -> %s)", migration["job_name"], migration["source_database"], migration["destination_database"])

    # 2. Resolve database credentials from environment variables
    if not SOURCE_DB_HOST or not DEST_DB_HOST:
        error_msg = "Source or destination database host is not configured"
        logger.error(error_msg)
        sys.exit(1)

    try:
        src_creds = get_source_credentials()
        dst_creds = get_destination_credentials()
    except Exception as exc:
        logger.error("Failed to resolve credentials: %s", exc)
        sys.exit(1)

    # 4. Connect to databases
    try:
        src_conn = psycopg2.connect(get_connection_string(src_creds))
        src_conn.autocommit = False
        logger.info("Connected to source database: %s", src_creds["host"])
    except psycopg2.Error as exc:
        logger.error("Failed to connect to source database: %s", exc)
        sys.exit(1)

    try:
        dst_conn = psycopg2.connect(get_connection_string(dst_creds))
        dst_conn.autocommit = False
        logger.info("Connected to destination database: %s", dst_creds["host"])
    except psycopg2.Error as exc:
        logger.error("Failed to connect to destination database: %s", exc)
        src_conn.close()
        sys.exit(1)

    # 5. Discover tables
    tables = discover_tables(src_conn)
    logger.info("Found %d tables: %s", len(tables), ", ".join(tables))

    if not tables:
        logger.warning("No tables found in source database")
        dst_conn.close()
        src_conn.close()
        sys.exit(0)

    # 6. Calculate total rows
    total_rows = 0
    for table in tables:
        total_rows += get_table_row_count(src_conn, table)
    logger.info("Total rows to migrate: %d", total_rows)

    # 7. Resume from checkpoint if available
    rows_already_migrated = migration.get("rows_migrated", 0) or 0

    # 8. Migrate each table
    overall_progress = 0.0
    try:
        for table in tables:
            logger.info("--- Processing table: %s ---", table)

            # Create table on destination if needed
            create_table_if_not_exists(dst_conn, src_conn, table)

            # Get row count for this table
            table_rows = get_table_row_count(src_conn, table)

            # Copy data
            copied = copy_table_in_batches(
                src_conn, dst_conn, table, migration_id, total_rows, rows_already_migrated
            )
            rows_already_migrated += copied

            if total_rows > 0:
                overall_progress = min((rows_already_migrated / total_rows) * 100.0, 100.0)

            logger.info(
                "Table '%s' complete: %d rows copied (overall progress: %.1f%%)",
                table,
                copied,
                overall_progress,
            )

        # 9. Mark migration as completed
        logger.info("Migration %d completed successfully (%d total rows)", migration_id, rows_already_migrated)
        api_post(
            "/migration-engine/status-update",
            {
                "migration_id": migration_id,
                "status": "COMPLETED",
                "progress_percent": 100.0,
                "rows_migrated": rows_already_migrated,
            },
        )

    except Exception as exc:
        logger.error("Migration %d failed: %s", migration_id, exc)
        try:
            api_post(
                "/migration-engine/status-update",
                {
                    "migration_id": migration_id,
                    "status": "FAILED",
                    "error": str(exc),
                    "progress_percent": overall_progress,
                    "rows_migrated": rows_already_migrated,
                },
            )
        except requests.RequestException:
            pass
        raise
    finally:
        src_conn.close()
        dst_conn.close()


if __name__ == "__main__":
    run_migration()
