"""SQL Server database validator using pyodbc."""

from __future__ import annotations

import logging
from typing import Any

from app.services.validators.base import BaseDatabaseValidator

logger = logging.getLogger(__name__)

# SQL Server binary column types
_SQLSERVER_BINARY_TYPES = frozenset({
    "binary", "varbinary", "image", "timestamp",
    "rowversion",
})


class SQLServerValidator(BaseDatabaseValidator):
    """Validates SQL Server connections, permissions, and discovers tables."""

    engine = "SQL_SERVER"

    def connect(self) -> None:
        import pyodbc

        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={self.host},{self.port};"
            f"DATABASE={self.database_name or 'master'};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"Encrypt=no;"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout={self.timeout};"
        )
        self._connection = pyodbc.connect(conn_str, timeout=self.timeout)
        logger.info("SQL Server connection established to %s:%s/%s", self.host, self.port, self.database_name)

    def close(self) -> None:
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def validate_connection(self) -> bool:
        with self._connection.cursor() as cur:
            cur.execute("SELECT 1")
            return True

    def database_exists(self) -> bool:
        with self._connection.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM sys.databases WHERE name = ?",
                (self.database_name,),
            )
            return cur.fetchone() is not None

    def discover_tables(self) -> list[str]:
        with self._connection.cursor() as cur:
            cur.execute("""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                  AND TABLE_CATALOG = ?
                  AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
                ORDER BY TABLE_NAME
            """, (self.database_name,))
            return [row[0] for row in cur.fetchall()]

    def validate_permissions(self) -> dict[str, bool]:
        perms: dict[str, bool] = {"SELECT": False, "INSERT": False, "CREATE": False}

        with self._connection.cursor() as cur:
            # Check CREATE TABLE permission
            cur.execute("""
                SELECT HAS_PERMS_BY_NAME(NULL, 'DATABASE', 'CREATE TABLE')
            """)
            row = cur.fetchone()
            perms["CREATE"] = bool(row[0]) if row else False

            # Check SELECT and INSERT on first user table
            tables = self.discover_tables()
            if tables:
                table = tables[0]
                cur.execute("""
                    SELECT
                        HAS_PERMS_BY_NAME(?, 'OBJECT', 'SELECT'),
                        HAS_PERMS_BY_NAME(?, 'OBJECT', 'INSERT')
                """, (table, table))
                row = cur.fetchone()
                if row:
                    perms["SELECT"] = bool(row[0])
                    perms["INSERT"] = bool(row[1])
            else:
                perms["SELECT"] = True
                perms["INSERT"] = True

        return perms

    def fetch_sample_rows(self, table: str, limit: int = 5) -> tuple[list[str], list[dict[str, Any]]]:
        with self._connection.cursor() as cur:
            # Get column info to exclude binary columns
            cur.execute("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_CATALOG = ? AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, (self.database_name, table))
            all_columns = cur.fetchall()

            safe_columns = [
                col_name for col_name, data_type in all_columns
                if data_type.lower() not in _SQLSERVER_BINARY_TYPES
            ]

            if not safe_columns:
                return [], []

            col_list = ", ".join(f"[{c}]" for c in safe_columns)
            cur.execute(f"SELECT TOP {limit} {col_list} FROM [{table}]", ())
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall()

            result_rows = []
            for row in rows:
                row_dict = {col: row[i] for i, col in enumerate(columns)}
                result_rows.append(row_dict)

            return safe_columns, result_rows

    def get_table_row_count(self, table: str) -> int | None:
        try:
            with self._connection.cursor() as cur:
                cur.execute("""
                    SELECT SUM(row_count)
                    FROM sys.dm_db_partition_stats
                    WHERE object_id = OBJECT_ID(?)
                      AND index_id IN (0, 1)
                """, (table,))
                row = cur.fetchone()
                if row and row[0] is not None:
                    return int(row[0])
        except Exception:
            pass
        return None
