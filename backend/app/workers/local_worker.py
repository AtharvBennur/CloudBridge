"""
Purpose:
Concrete implementation of the migration worker for actual database migration.
Runs in a background thread, performs real multi-table data migration in chunks,
transient failures, retries, checkpointing, and heartbeats.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any

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

try:
    import pymysql
    import pymysql.cursors
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

from flask import Flask

from app.extensions import db
from app.models.aws_connection import AWSConnection
from app.models.database_config import DatabaseConfig
from app.models.migration import MigrationJob, MigrationStatus
from app.models.migration_checkpoint import MigrationCheckpoint
from app.workers.base_worker import BaseMigrationWorker

logger = logging.getLogger(__name__)


class LocalMigrationWorker(threading.Thread, BaseMigrationWorker):
    """Performs actual chunk-by-chunk database migration in a background thread."""

    def __init__(self, app: Flask, migration_id: int) -> None:
        super().__init__()
        self.app = app
        self.migration_id = migration_id
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._status = MigrationStatus.PENDING
        self._progress = 0.0
        self._last_heartbeat = datetime.utcnow()

    def run(self) -> None:
        self._status = MigrationStatus.RUNNING
        self.heartbeat()

        with self.app.app_context():
            job = MigrationJob.query.get(self.migration_id)
            if not job:
                self.app.logger.error(f"Migration job {self.migration_id} not found in database.")
                self._status = MigrationStatus.FAILED
                return

            self.app.logger.info(f"Migration Started: Job {job.id} ({job.job_name})")

            # Get database configurations
            src_config = DatabaseConfig.query.get(job.source_database_config_id)
            dst_config = DatabaseConfig.query.get(job.destination_database_config_id)
            
            if not src_config or not dst_config:
                job.status = MigrationStatus.FAILED
                job.error_message = f"Source or destination database configuration not found. Source config ID: {job.source_database_config_id}, Dest config ID: {job.destination_database_config_id}"
                db.session.commit()
                self._status = MigrationStatus.FAILED
                self.app.logger.error(f"Migration failed: Database configs not found. Source: {src_config}, Dest: {dst_config}")
                return

            self.app.logger.info(f"Database configs found. Source: {src_config.name} ({src_config.host}), Dest: {dst_config.name} ({dst_config.host})")

            # Check database driver availability
            if src_config.database_type == "MYSQL" and not MYSQL_AVAILABLE:
                job.status = MigrationStatus.FAILED
                job.error_message = "PyMySQL driver not installed. Cannot connect to MySQL database."
                db.session.commit()
                self._status = MigrationStatus.FAILED
                self.app.logger.error("Migration failed: PyMySQL driver not installed")
                return
            
            if src_config.database_type == "POSTGRESQL" and not POSTGRESQL_AVAILABLE:
                job.status = MigrationStatus.FAILED
                job.error_message = "psycopg2 driver not installed. Cannot connect to PostgreSQL database."
                db.session.commit()
                self._status = MigrationStatus.FAILED
                self.app.logger.error("Migration failed: psycopg2 driver not installed")
                return

            try:
                # Connect to databases
                self.app.logger.info(f"Attempting to connect to source database: {src_config.host}:{src_config.port}")
                src_conn = self._get_db_connection(src_config)
                self.app.logger.info(f"Attempting to connect to destination database: {dst_config.host}:{dst_config.port}")
                dst_conn = self._get_db_connection(dst_config)
                
                self.app.logger.info(f"Successfully connected to source database: {src_config.host}")
                self.app.logger.info(f"Successfully connected to destination database: {dst_config.host}")

                # Discover tables
                tables = self._discover_tables(src_conn, src_config.database_type)
                self.app.logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")

                if not tables:
                    self.app.logger.warning("No tables found in source database")
                    job.status = MigrationStatus.COMPLETED
                    job.completed_at = datetime.utcnow()
                    db.session.commit()
                    self._status = MigrationStatus.COMPLETED
                    return

                # Calculate total rows
                total_rows = 0
                for table in tables:
                    total_rows += self._get_table_row_count(src_conn, table, src_config.database_type)
                job.total_rows = total_rows
                db.session.commit()
                self.app.logger.info(f"Total rows to migrate: {total_rows}")

                # Resume from checkpoint if available
                rows_migrated = job.rows_migrated or 0
                latest_checkpoint = (
                    MigrationCheckpoint.query.filter_by(migration_id=self.migration_id)
                    .order_by(MigrationCheckpoint.created_at.desc())
                    .first()
                )
                if latest_checkpoint:
                    rows_migrated = latest_checkpoint.rows_processed
                    self.app.logger.info(
                        f"Resuming job {job.id} from checkpoint '{latest_checkpoint.checkpoint_name}' with {rows_migrated} rows processed."
                    )

                chunk_size = job.chunk_size or 1000

                # Migrate each table
                for table in tables:
                    # Check for stop/pause
                    if self._should_stop(job):
                        return

                    self.app.logger.info(f"--- Processing table: {table} ---")
                    job.current_table = table
                    db.session.commit()

                    # Create table on destination if needed
                    self._create_table_if_not_exists(dst_conn, src_conn, table, src_config.database_type, dst_config.database_type)

                    # Get row count for this table
                    table_rows = self._get_table_row_count(src_conn, table, src_config.database_type)

                    # Copy data
                    copied = self._copy_table_in_batches(
                        src_conn, dst_conn, table, job, total_rows, rows_migrated,
                        src_config.database_type, dst_config.database_type, chunk_size
                    )
                    rows_migrated += copied

                    # Update progress
                    if total_rows > 0:
                        self._progress = min((rows_migrated / total_rows) * 100.0, 100.0)
                    else:
                        self._progress = 100.0

                    job.rows_migrated = rows_migrated
                    job.progress_percent = self._progress
                    db.session.commit()

                    # Save checkpoint
                    checkpoint_name = f"checkpoint_{table}_{rows_migrated}"
                    checkpoint = MigrationCheckpoint(
                        migration_id=self.migration_id,
                        checkpoint_name=checkpoint_name,
                        progress_percent=self._progress,
                        rows_processed=rows_migrated,
                        checkpoint_metadata=f'{{"table": "{table}", "rows_migrated": {copied}, "timestamp": {time.time()}}}',
                    )
                    db.session.add(checkpoint)
                    db.session.commit()
                    self.app.logger.info(f"Checkpoint Saved: '{checkpoint_name}' for job {job.id}")

                    self.app.logger.info(
                        f"Table '{table}' complete: {copied} rows copied (overall progress: {self._progress:.1f}%)"
                    )

                # Mark completed
                job.status = MigrationStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.progress_percent = 100.0
                db.session.commit()
                self._status = MigrationStatus.COMPLETED
                self.app.logger.info(f"Migration Finished: Job {job.id} completed successfully ({rows_migrated} total rows)")

                # Close connections
                src_conn.close()
                dst_conn.close()

            except Exception as exc:
                import traceback
                self.app.logger.error(f"Migration Failed: Job {job.id} failed with error: {exc}")
                self.app.logger.error(f"Full traceback: {traceback.format_exc()}")
                job.status = MigrationStatus.FAILED
                job.error_message = f"{type(exc).__name__}: {str(exc)}"
                job.completed_at = datetime.utcnow()
                db.session.commit()
                self._status = MigrationStatus.FAILED

    def _should_stop(self, job: MigrationJob) -> bool:
        """Check if migration should be stopped or paused."""
        db.session.expire(job)
        job = MigrationJob.query.get(self.migration_id)
        if not job:
            return True

        if job.status == MigrationStatus.PAUSED or self._pause_event.is_set():
            self.app.logger.info(f"Migration job {self.migration_id} paused.")
            self._status = MigrationStatus.PAUSED
            return True
        if job.status == MigrationStatus.CANCELLED or self._stop_event.is_set():
            self.app.logger.info(f"Migration job {self.migration_id} cancelled.")
            self._status = MigrationStatus.CANCELLED
            return True
        return False

    def _get_db_connection(self, config: DatabaseConfig):
        """Get database connection based on configuration."""
        if config.database_type == "MYSQL":
            if not MYSQL_AVAILABLE:
                raise RuntimeError("PyMySQL is not installed. Cannot connect to MySQL database.")
            return pymysql.connect(
                host=config.host,
                port=config.port,
                user=config.username,
                password=config.password,
                database=config.database_name,
                connect_timeout=10,
                cursorclass=pymysql.cursors.DictCursor,
                charset='utf8mb4',
            )
        else:  # POSTGRESQL
            if not POSTGRESQL_AVAILABLE:
                raise RuntimeError("psycopg2 is not installed. Cannot connect to PostgreSQL database.")
            conn_str = (
                f"host={config.host} port={config.port} "
                f"dbname={config.database_name} user={config.username} "
                f"password={config.password} sslmode=require connect_timeout=10"
            )
            conn = psycopg2.connect(conn_str)
            conn.autocommit = False
            return conn

    def _discover_tables(self, conn, engine: str) -> list[str]:
        """Return list of user tables in the database."""
        if engine == "MYSQL":
            if not MYSQL_AVAILABLE:
                raise RuntimeError("PyMySQL is not installed. Cannot discover MySQL tables.")
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
            if not POSTGRESQL_AVAILABLE:
                raise RuntimeError("psycopg2 is not installed. Cannot discover PostgreSQL tables.")
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                )
                return [row[0] for row in cur.fetchall()]

    def _get_table_row_count(self, conn, table: str, engine: str) -> int:
        """Get row count for a table."""
        if engine == "MYSQL":
            if not MYSQL_AVAILABLE:
                raise RuntimeError("PyMySQL is not installed. Cannot get MySQL table row count.")
            with conn.cursor() as cur:
                cur.execute(f'SELECT COUNT(*) as cnt FROM `{table}`')
                result = cur.fetchone()
                return result['cnt'] if isinstance(result, dict) else result[0]
        else:  # POSTGRESQL
            if not POSTGRESQL_AVAILABLE:
                raise RuntimeError("psycopg2 is not installed. Cannot get PostgreSQL table row count.")
            with conn.cursor() as cur:
                cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                return cur.fetchone()[0]

    def _get_table_columns(self, conn, table: str, engine: str) -> list[tuple[str, str]]:
        """Return list of (column_name, data_type) for a table."""
        if engine == "MYSQL":
            if not MYSQL_AVAILABLE:
                raise RuntimeError("PyMySQL is not installed. Cannot get MySQL table columns.")
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
            if not POSTGRESQL_AVAILABLE:
                raise RuntimeError("psycopg2 is not installed. Cannot get PostgreSQL table columns.")
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

    def _create_table_if_not_exists(self, dst_conn, src_conn, table: str, src_engine: str, dest_engine: str) -> None:
        """Create the table on destination if it doesn't exist."""
        # Check if table exists on destination
        if dest_engine == "MYSQL":
            if not MYSQL_AVAILABLE:
                raise RuntimeError("PyMySQL is not installed. Cannot check MySQL table existence.")
            with dst_conn.cursor() as cur:
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
            if not POSTGRESQL_AVAILABLE:
                raise RuntimeError("psycopg2 is not installed. Cannot check PostgreSQL table existence.")
            with dst_conn.cursor() as cur:
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
            self.app.logger.info(f"Table '{table}' already exists on destination")
            return

        columns = self._get_table_columns(src_conn, table, src_engine)
        if not columns:
            self.app.logger.warning(f"Table '{table}' has no columns, skipping")
            return

        # Build CREATE TABLE statement based on destination engine
        if dest_engine == "MYSQL":
            col_defs = ", ".join(f'`{name}` {dtype.upper()}' for name, dtype in columns)
            create_sql = f'CREATE TABLE IF NOT EXISTS `{table}` ({col_defs})'
        else:  # POSTGRESQL
            col_defs = ", ".join(f'"{name}" {dtype.upper()}' for name, dtype in columns)
            create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({col_defs})'

        with dst_conn.cursor() as cur:
            cur.execute(create_sql)
        dst_conn.commit()
        self.app.logger.info(f"Created table '{table}' on destination")

    def _copy_table_in_batches(
        self, src_conn, dst_conn, table: str, job: MigrationJob, total_rows: int,
        rows_already_migrated: int, src_engine: str, dest_engine: str, chunk_size: int
    ) -> int:
        """Copy rows from source to destination in batches. Returns rows copied."""
        columns = self._get_table_columns(src_conn, table, src_engine)
        col_names = [c[0] for c in columns]
        
        # Build column list and placeholders based on engine
        if src_engine == "MYSQL":
            if not MYSQL_AVAILABLE:
                raise RuntimeError("PyMySQL is not installed. Cannot copy MySQL table data.")
            col_list = ", ".join(f'`{c}`' for c in col_names)
        else:  # POSTGRESQL
            if not POSTGRESQL_AVAILABLE:
                raise RuntimeError("psycopg2 is not installed. Cannot copy PostgreSQL table data.")
            col_list = ", ".join(f'"{c}"' for c in col_names)
        
        placeholders = ", ".join(["%s"] * len(col_names))

        rows_copied = 0
        offset = rows_already_migrated

        while True:
            # Check for stop/pause
            if self._should_stop(job):
                break

            with src_conn.cursor() as cur:
                if src_engine == "MYSQL":
                    cur.execute(
                        f'SELECT {col_list} FROM `{table}` LIMIT %s OFFSET %s',
                        (chunk_size, offset),
                    )
                else:  # POSTGRESQL
                    cur.execute(
                        f'SELECT {col_list} FROM "{table}" LIMIT %s OFFSET %s',
                        (chunk_size, offset),
                    )
                rows = cur.fetchall()

            if not rows:
                break

            with dst_conn.cursor() as cur:
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
            dst_conn.commit()

            rows_copied += len(rows)
            offset += len(rows)
            total_copied = rows_already_migrated + rows_copied

            # Update progress
            if total_rows > 0:
                progress = min((total_copied / total_rows) * 100.0, 100.0)
            else:
                progress = 100.0

            job.progress_percent = progress
            job.rows_migrated = total_copied
            db.session.commit()

            self.app.logger.info(
                f"Table '{table}': copied {len(rows)} rows (total: {total_copied}, progress: {progress:.1f}%)"
            )

            # Heartbeat
            self.heartbeat()

        return rows_copied

    # BaseMigrationWorker implementation
    def start(self) -> None:
        super().start()

    def pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()
        if not self.is_alive():
            super().start()

    def cancel(self) -> None:
        self._stop_event.set()

    def get_status(self) -> str:
        return self._status

    def get_progress(self) -> float:
        return self._progress

    def heartbeat(self) -> None:
        self._last_heartbeat = datetime.utcnow()
        self.app.logger.info(f"Worker Status: Heartbeat for job {self.migration_id} updated at {self._last_heartbeat}")

    def retry(self) -> None:
        """Restart a failed worker from its persisted checkpoint."""
        if not self.is_alive():
            super().start()
