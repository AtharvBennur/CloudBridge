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
import requests
from botocore.exceptions import ClientError

# Database drivers - support both PostgreSQL and MySQL
try:
    import psycopg2
    import psycopg2.extras
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

try:
    import pymysql
    import pymysql.cursors
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

# Required environment variables
CLOUDBRIDGE_API_URL = os.getenv("CLOUDBRIDGE_API_URL")
if not CLOUDBRIDGE_API_URL:
    logging.error("CLOUDBRIDGE_API_URL is not set - cannot contact CloudBridge API")
    sys.exit(1)

MIGRATION_ID = os.getenv("MIGRATION_ID")
if not MIGRATION_ID:
    logging.error("MIGRATION_ID is not set - cannot proceed")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("migration-worker")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_URL = CLOUDBRIDGE_API_URL.rstrip("/")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# Shared secret for internal worker API calls
WORKER_API_SECRET = os.environ.get("WORKER_API_SECRET", "")
if not WORKER_API_SECRET:
    # Fall back to SECRET_KEY if WORKER_API_SECRET is not set
    WORKER_API_SECRET = os.environ.get("SECRET_KEY", "") or "cloudbridge-worker-secret"
    logger.warning("WORKER_API_SECRET not set, falling back to SECRET_KEY")
WORKER_API_SECRET = WORKER_API_SECRET.strip()

# Source DB credentials (passed as env vars by ECS task)
SOURCE_DB_HOST = os.environ.get("SOURCE_DB_HOST", "")
SOURCE_DB_PORT = int(os.environ.get("SOURCE_DB_PORT", "5432"))
SOURCE_DB_USERNAME = os.environ.get("SOURCE_DB_USERNAME", "")
SOURCE_DB_PASSWORD = os.environ.get("SOURCE_DB_PASSWORD", "")
SOURCE_DB_NAME = os.environ.get("SOURCE_DB_NAME", "")
SOURCE_DB_SECRET_ARN = os.environ.get("SOURCE_DB_SECRET_ARN", "")
SOURCE_DB_ENGINE = os.environ.get("SOURCE_DB_ENGINE", "POSTGRESQL").upper()  # POSTGRESQL or MYSQL

# Destination DB credentials (passed as env vars by ECS task)
DEST_DB_HOST = os.environ.get("DEST_DB_HOST", "")
DEST_DB_PORT = int(os.environ.get("DEST_DB_PORT", "5432"))
DEST_DB_USERNAME = os.environ.get("DEST_DB_USERNAME", "")
DEST_DB_PASSWORD = os.environ.get("DEST_DB_PASSWORD", "")
DEST_DB_NAME = os.environ.get("DEST_DB_NAME", "")
DEST_DB_SECRET_ARN = os.environ.get("DEST_DB_SECRET_ARN", "")
DEST_DB_ENGINE = os.environ.get("DEST_DB_ENGINE", "POSTGRESQL").upper()  # POSTGRESQL or MYSQL

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "5000"))
PROGRESS_REPORT_INTERVAL = int(os.environ.get("PROGRESS_REPORT_INTERVAL", "5000"))

# ---------------------------------------------------------------------------
# CloudBridge API client
# ---------------------------------------------------------------------------


def _worker_headers() -> dict[str, str]:
    """Build headers for internal worker API calls."""
    return {
        "Content-Type": "application/json",
        "X-Worker-Secret": WORKER_API_SECRET,
    }


def api_get(path: str) -> dict[str, Any]:
    resp = requests.get(f"{API_URL}{path}", headers=_worker_headers(), timeout=60)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    resp = requests.post(f"{API_URL}{path}", json=payload, headers=_worker_headers(), timeout=60)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Database credential resolution
# ---------------------------------------------------------------------------


def resolve_secret_credentials(secret_arn: str, region: str) -> dict[str, str]:
    """Retrieve database credentials from AWS Secrets Manager."""
    logger.info("Retrieving credentials from Secrets Manager: %s", secret_arn)
    
    # Try to use AWS credentials from environment if available
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    
    if aws_access_key_id and aws_secret_access_key:
        logger.info("Using AWS credentials from environment variables")
        sm_client = boto3.client(
            "secretsmanager", 
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
    else:
        logger.info("Using default AWS credentials chain (IAM role)")
        sm_client = boto3.client("secretsmanager", region_name=region)
    
    try:
        response = sm_client.get_secret_value(SecretId=secret_arn)
        return json.loads(response.get("SecretString", "{}"))
    except ClientError as exc:
        raise RuntimeError(f"Failed to retrieve secret {secret_arn}: {exc}") from exc


def get_source_credentials() -> dict[str, Any]:
    """Build source database connection parameters."""
    # Try to get password from environment variables first (set by ECS)
    password = SOURCE_DB_PASSWORD
    if not password and SOURCE_DB_SECRET_ARN:
        # Fall back to Secrets Manager
        logger.info(f"Password not provided in env, fetching from Secrets Manager: {SOURCE_DB_SECRET_ARN}")
        try:
            secret = resolve_secret_credentials(SOURCE_DB_SECRET_ARN, AWS_REGION)
            password = secret.get("password", "")
        except Exception as exc:
            logger.error(f"Failed to retrieve secret from Secrets Manager: {exc}")
            logger.warning("Continuing without password - this will likely fail")
    
    if not password:
        logger.error("Source database password not available - neither in env nor in Secrets Manager")
        raise RuntimeError("Source database password not available - migration cannot proceed")
    
    return {
        "host": SOURCE_DB_HOST,
        "port": SOURCE_DB_PORT,
        "username": SOURCE_DB_USERNAME,
        "password": password,
        "database": SOURCE_DB_NAME,
    }


def get_destination_credentials() -> dict[str, Any]:
    """Build destination database connection parameters."""
    # Try to get password from environment variables first (set by ECS)
    password = DEST_DB_PASSWORD
    if not password and DEST_DB_SECRET_ARN:
        # Fall back to Secrets Manager
        logger.info(f"Password not provided in env, fetching from Secrets Manager: {DEST_DB_SECRET_ARN}")
        try:
            secret = resolve_secret_credentials(DEST_DB_SECRET_ARN, AWS_REGION)
            password = secret.get("password", "")
        except Exception as exc:
            logger.error(f"Failed to retrieve secret from Secrets Manager: {exc}")
            logger.warning("Continuing without password - this will likely fail")
    
    if not password:
        logger.error("Destination database password not available - neither in env nor in Secrets Manager")
        raise RuntimeError("Destination database password not available - migration cannot proceed")
    
    return {
        "host": DEST_DB_HOST,
        "port": DEST_DB_PORT,
        "username": DEST_DB_USERNAME,
        "password": password,
        "database": DEST_DB_NAME,
    }


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------


def get_connection_string(creds: dict[str, Any], engine: str = "POSTGRESQL") -> str:
    """Build connection string based on database engine."""
    if engine == "MYSQL":
        return (
            f"host={creds['host']} port={creds['port']} "
            f"dbname={creds['database']} user={creds['username']} "
            f"password={creds['password']} connect_timeout=300"
        )
    else:  # POSTGRESQL (default)
        return (
            f"host={creds['host']} port={creds['port']} "
            f"dbname={creds['database']} user={creds['username']} "
            f"password={creds['password']} sslmode=prefer connect_timeout=300"
        )


def get_db_connection(creds: dict[str, Any], engine: str = "POSTGRESQL"):
    """Get database connection based on engine type."""
    if engine == "MYSQL":
        if not MYSQL_AVAILABLE:
            raise RuntimeError("PyMySQL is not installed. Cannot connect to MySQL database.")
        logger.info(f"Connecting to MySQL: {creds['host']}:{creds['port']} as {creds['username']}")
        conn = pymysql.connect(
            host=creds['host'],
            port=creds['port'],
            user=creds['username'],
            password=creds['password'],
            database=creds['database'],
            connect_timeout=300,
            read_timeout=300,
            write_timeout=300,
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4',
        )
        return conn
    else:  # POSTGRESQL (default)
        if not POSTGRESQL_AVAILABLE:
            raise RuntimeError("psycopg2 is not installed. Cannot connect to PostgreSQL database.")
        logger.info(f"Connecting to PostgreSQL: {creds['host']}:{creds['port']} as {creds['username']}")
        conn = psycopg2.connect(get_connection_string(creds, engine))
        conn.autocommit = False
        return conn


def discover_tables(conn, engine: str = "POSTGRESQL") -> list[str]:
    """Return list of user tables in the source database."""
    if engine == "MYSQL":
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            return [row['table_name'] for row in cur.fetchall()]
    else:  # POSTGRESQL
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            return [row[0] for row in cur.fetchall()]


def get_table_row_count(conn, table: str, engine: str = "POSTGRESQL") -> int:
    if engine == "MYSQL":
        with conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) as cnt FROM `{table}`')
            result = cur.fetchone()
            return result['cnt'] if isinstance(result, dict) else result[0]
    else:  # POSTGRESQL
        with conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            return cur.fetchone()[0]


def get_table_columns(conn, table: str, engine: str = "POSTGRESQL") -> list[tuple[str, str]]:
    """Return list of (column_name, data_type) for a table."""
    if engine == "MYSQL":
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table,),
            )
            return [(row['column_name'], row['data_type']) for row in cur.fetchall()]
    else:  # POSTGRESQL
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


def create_table_if_not_exists(dest_conn, src_conn, table: str, src_engine: str = "POSTGRESQL", dest_engine: str = "POSTGRESQL") -> None:
    """Create the table on destination if it doesn't exist, matching source schema."""
    # Check if table exists on destination
    if dest_engine == "MYSQL":
        with dest_conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = DATABASE() AND table_name = %s
                ) as exists
                """,
                (table,),
            )
            result = cur.fetchone()
            exists = result['exists'] if isinstance(result, dict) else result[0]
    else:  # POSTGRESQL
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

    columns = get_table_columns(src_conn, table, src_engine)
    if not columns:
        logger.warning("Table '%s' has no columns, skipping", table)
        return

    # Build CREATE TABLE statement based on destination engine
    if dest_engine == "MYSQL":
        col_defs = ", ".join(f'`{name}` {dtype.upper()}' for name, dtype in columns)
        create_sql = f'CREATE TABLE IF NOT EXISTS `{table}` ({col_defs})'
    else:  # POSTGRESQL
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
    src_engine: str = "POSTGRESQL",
    dest_engine: str = "POSTGRESQL",
) -> int:
    """Copy rows from source to destination in batches. Returns rows copied."""
    columns = get_table_columns(src_conn, table, src_engine)
    col_names = [c[0] for c in columns]
    
    # Build column list and placeholders based on engine
    if src_engine == "MYSQL":
        col_list = ", ".join(f'`{c}`' for c in col_names)
    else:  # POSTGRESQL
        col_list = ", ".join(f'"{c}"' for c in col_names)
    
    placeholders = ", ".join(["%s"] * len(col_names))

    rows_copied = 0
    offset = rows_already_migrated

    while True:
        with src_conn.cursor() as cur:
            if src_engine == "MYSQL":
                cur.execute(
                    f'SELECT {col_list} FROM `{table}` LIMIT %s OFFSET %s',
                    (BATCH_SIZE, offset),
                )
            else:  # POSTGRESQL
                cur.execute(
                    f'SELECT {col_list} FROM "{table}" LIMIT %s OFFSET %s',
                    (BATCH_SIZE, offset),
                )
            rows = cur.fetchall()

        if not rows:
            break

        with dest_conn.cursor() as cur:
            for row in rows:
                # Convert dict to tuple if using MySQL DictCursor
                if isinstance(row, dict):
                    row_values = tuple(row[c] for c in col_names)
                else:
                    row_values = row
                
                if dest_engine == "MYSQL":
                    cur.execute(
                        f'INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})',
                        row_values,
                    )
                else:  # POSTGRESQL
                    cur.execute(
                        f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
                        row_values,
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
                f"/worker/migrations/{migration_id}/checkpoint",
                {
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

    # 1. Fetch migration details from internal worker API
    try:
        migration = api_get(f"/worker/migrations/{migration_id}")
    except requests.RequestException as exc:
        logger.error("Failed to fetch migration: %s", exc)
        try:
            api_post(
                f"/worker/migrations/{migration_id}/status",
                {"status": "FAILED", "error": str(exc)},
            )
        except Exception:
            pass
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
        src_conn = get_db_connection(src_creds, SOURCE_DB_ENGINE)
        logger.info("Connected to source database: %s (engine: %s)", src_creds["host"], SOURCE_DB_ENGINE)
    except Exception as exc:
        logger.error("Failed to connect to source database: %s", exc)
        sys.exit(1)

    try:
        dst_conn = get_db_connection(dst_creds, DEST_DB_ENGINE)
        logger.info("Connected to destination database: %s (engine: %s)", dst_creds["host"], DEST_DB_ENGINE)
    except Exception as exc:
        logger.error("Failed to connect to destination database: %s", exc)
        src_conn.close()
        sys.exit(1)

    # 5. Discover tables
    tables = discover_tables(src_conn, SOURCE_DB_ENGINE)
    logger.info("Found %d tables: %s", len(tables), ", ".join(tables))

    if not tables:
        logger.warning("No tables found in source database")
        dst_conn.close()
        src_conn.close()
        sys.exit(0)

    # 6. Calculate total rows
    total_rows = 0
    for table in tables:
        total_rows += get_table_row_count(src_conn, table, SOURCE_DB_ENGINE)
    logger.info("Total rows to migrate: %d", total_rows)

    # 7. Resume from checkpoint if available
    rows_already_migrated = migration.get("rows_migrated", 0) or 0

    # 8. Migrate each table
    overall_progress = 0.0
    try:
        for table in tables:
            logger.info("--- Processing table: %s ---", table)

            # Create table on destination if needed
            create_table_if_not_exists(dst_conn, src_conn, table, SOURCE_DB_ENGINE, DEST_DB_ENGINE)

            # Get row count for this table
            table_rows = get_table_row_count(src_conn, table, SOURCE_DB_ENGINE)

            # Copy data
            copied = copy_table_in_batches(
                src_conn, dst_conn, table, migration_id, total_rows, rows_already_migrated,
                SOURCE_DB_ENGINE, DEST_DB_ENGINE
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
            f"/worker/migrations/{migration_id}/status",
            {
                "status": "COMPLETED",
                "progress_percent": 100.0,
                "rows_migrated": rows_already_migrated,
            },
        )

    except Exception as exc:
        logger.error("Migration %d failed: %s", migration_id, exc)
        try:
            api_post(
                f"/worker/migrations/{migration_id}/status",
                {
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
