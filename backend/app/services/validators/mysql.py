"""MySQL database validator using PyMySQL with production-grade error handling."""

from __future__ import annotations

import logging
import traceback
from typing import Any

import pymysql

from app.services.validators.base import BaseDatabaseValidator
from app.services.validators.sensitive_masker import is_binary_column

logger = logging.getLogger(__name__)

# System schemas to exclude from table discovery
_SYSTEM_SCHEMAS = frozenset({"information_schema", "mysql", "performance_schema", "sys"})

# MySQL binary column types
_MYSQL_BINARY_TYPES = frozenset({
    "blob", "longblob", "mediumblob", "tinyblob",
    "binary", "varbinary", "geometry", "point",
    "linestring", "polygon", "multipoint", "multilinestring",
    "multipolygon", "geometrycollection",
})


class MySQLValidator(BaseDatabaseValidator):
    """Validates MySQL connections, permissions, and discovers tables.
    
    Production-grade implementation with:
    - Detailed logging at each step
    - Proper timeout configuration
    - SSL disabled for EC2/RDS compatibility
    - Full exception tracebacks
    """

    engine = "MYSQL"

    def connect(self) -> None:
        """Open MySQL connection with comprehensive logging and error handling.
        
        This method performs:
        1. TCP connection
        2. MySQL protocol handshake
        3. Authentication
        4. Database selection (if specified)
        
        All steps are handled by pymysql.connect() internally.
        """
        logger.info(
            "MySQL connection attempt: host=%s port=%s user=%s database=%s timeout=%ss",
            self.host, self.port, self.username, self.database_name or "(none)", self.timeout
        )
        
        try:
            # Set socket timeout explicitly for Windows compatibility
            import socket
            socket.setdefaulttimeout(self.timeout)
            
            # PyMySQL handles TCP + handshake + auth in one call
            # We disable SSL for EC2/RDS compatibility
            self._connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=self.database_name or "",
                connect_timeout=self.timeout,
                read_timeout=self.timeout,
                write_timeout=self.timeout,
                cursorclass=pymysql.cursors.DictCursor,
                charset="utf8mb4",
                ssl_disabled=True,  # Critical for EC2 MySQL without SSL
            )
            
            logger.info(
                "✓ MySQL connection SUCCESS: host=%s port=%s database=%s",
                self.host, self.port, self.database_name or "(none)"
            )
            
        except pymysql.err.OperationalError as exc:
            # OperationalError includes TCP, handshake, and auth failures
            error_code = exc.args[0] if exc.args else None
            error_msg = exc.args[1] if len(exc.args) > 1 else str(exc)
            
            logger.error(
                "✗ MySQL connection FAILED: host=%s port=%s error_code=%s error=%s",
                self.host, self.port, error_code, error_msg
            )
            logger.error("Full exception traceback:\n%s", traceback.format_exc())
            
            # Re-raise with structured error info
            raise RuntimeError(
                f"MySQL connection failed (error {error_code}): {error_msg}"
            ) from exc
            
        except Exception as exc:
            logger.error(
                "✗ MySQL connection FAILED with unexpected error: host=%s port=%s error=%s",
                self.host, self.port, exc
            )
            logger.error("Full exception traceback:\n%s", traceback.format_exc())
            raise

    def close(self) -> None:
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def validate_connection(self) -> bool:
        """Execute SELECT 1 to verify connection is working."""
        logger.debug("Executing SELECT 1 to verify connection")
        try:
            with self._connection.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                logger.debug("✓ SELECT 1 succeeded: %s", result)
                return True
        except Exception as exc:
            logger.error("✗ SELECT 1 failed: %s", exc)
            logger.error("Traceback:\n%s", traceback.format_exc())
            raise

    def database_exists(self) -> bool:
        """Check if the target database exists."""
        logger.debug("Checking if database '%s' exists", self.database_name)
        try:
            with self._connection.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                    (self.database_name,),
                )
                exists = cur.fetchone() is not None
                logger.debug("✓ Database '%s' exists: %s", self.database_name, exists)
                return exists
        except Exception as exc:
            logger.error("✗ Database existence check failed: %s", exc)
            logger.error("Traceback:\n%s", traceback.format_exc())
            raise

    def discover_tables(self) -> list[str]:
        """Discover all user tables in the database."""
        logger.debug("Discovering tables in database '%s'", self.database_name)
        try:
            with self._connection.cursor() as cur:
                cur.execute("""
                    SELECT TABLE_NAME
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_NAME
                """, (self.database_name,))
                tables = [row["TABLE_NAME"] for row in cur.fetchall()]
                logger.debug("✓ Discovered %d tables: %s", len(tables), tables[:5])
                return tables
        except Exception as exc:
            logger.error("✗ Table discovery failed: %s", exc)
            logger.error("Traceback:\n%s", traceback.format_exc())
            raise

    def validate_permissions(self) -> dict[str, bool]:
        """Validate user permissions by checking SHOW GRANTS."""
        logger.debug("Validating permissions for user '%s'", self.username)
        perms: dict[str, bool] = {"SELECT": False, "INSERT": False, "CREATE": False}

        try:
            with self._connection.cursor() as cur:
                cur.execute("SHOW GRANTS FOR CURRENT_USER()")
                grants = cur.fetchall()
                logger.debug("Retrieved %d GRANT statements", len(grants))

            for grant_row in grants:
                grant_str = list(grant_row.values())[0].upper()
                logger.debug("Processing GRANT: %s", grant_str[:100])
                
                if "ALL PRIVILEGES" in grant_str or "GRANT ALL" in grant_str:
                    logger.debug("✓ User has ALL PRIVILEGES")
                    return {"SELECT": True, "INSERT": True, "CREATE": True}
                if "SELECT" in grant_str:
                    perms["SELECT"] = True
                if "INSERT" in grant_str:
                    perms["INSERT"] = True
                if "CREATE" in grant_str:
                    perms["CREATE"] = True

            logger.debug("✓ Permissions validated: SELECT=%s INSERT=%s CREATE=%s", 
                        perms["SELECT"], perms["INSERT"], perms["CREATE"])
            return perms
            
        except Exception as exc:
            logger.error("✗ Permission validation failed: %s", exc)
            logger.error("Traceback:\n%s", traceback.format_exc())
            raise

    def fetch_sample_rows(self, table: str, limit: int = 5) -> tuple[list[str], list[dict[str, Any]]]:
        with self._connection.cursor() as cur:
            # Get column info to exclude binary columns
            cur.execute("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (self.database_name, table))
            all_columns = cur.fetchall()

            safe_columns = [
                row["COLUMN_NAME"] for row in all_columns
                if not is_binary_column(row["DATA_TYPE"])
            ]

            if not safe_columns:
                return [], []

            col_list = ", ".join(f"`{c}`" for c in safe_columns)
            cur.execute(f"SELECT {col_list} FROM `{table}` LIMIT %s", (limit,))
            rows = cur.fetchall()

            result_rows = []
            for row in rows:
                row_dict = {col: row[col] for col in safe_columns}
                result_rows.append(row_dict)

            return safe_columns, result_rows

    def get_table_row_count(self, table: str) -> int | None:
        try:
            with self._connection.cursor() as cur:
                cur.execute("""
                    SELECT TABLE_ROWS
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, (self.database_name, table))
                row = cur.fetchone()
                if row and row.get("TABLE_ROWS") is not None:
                    return int(row["TABLE_ROWS"])
        except Exception:
            pass
        return None

    def execute_verify_query(self) -> None:
        """Execute a verification query to ensure connection is genuinely working."""
        logger.debug("Executing verification query: SELECT VERSION()")
        try:
            with self._connection.cursor() as cur:
                cur.execute("SELECT VERSION()")
                result = cur.fetchone()
                logger.debug("✓ Verification query successful: MySQL version %s", result)
        except Exception as exc:
            logger.error("✗ Verification query failed: %s", exc)
            logger.error("Traceback:\n%s", traceback.format_exc())
            raise
