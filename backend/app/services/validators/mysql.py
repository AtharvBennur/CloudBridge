"""MySQL database validator using PyMySQL."""

from __future__ import annotations

import logging
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
    """Validates MySQL connections, permissions, and discovers tables."""

    engine = "MYSQL"

    def connect(self) -> None:
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
        )
        logger.info("MySQL connection established to %s:%s/%s", self.host, self.port, self.database_name)

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
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (self.database_name,),
            )
            return cur.fetchone() is not None

    def discover_tables(self) -> list[str]:
        with self._connection.cursor() as cur:
            cur.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """, (self.database_name,))
            return [row["TABLE_NAME"] for row in cur.fetchall()]

    def validate_permissions(self) -> dict[str, bool]:
        perms: dict[str, bool] = {"SELECT": False, "INSERT": False, "CREATE": False}

        with self._connection.cursor() as cur:
            cur.execute("SHOW GRANTS FOR CURRENT_USER()")
            grants = cur.fetchall()

        for grant_row in grants:
            grant_str = list(grant_row.values())[0].upper()
            if "ALL PRIVILEGES" in grant_str or "GRANT ALL" in grant_str:
                return {"SELECT": True, "INSERT": True, "CREATE": True}
            if "SELECT" in grant_str:
                perms["SELECT"] = True
            if "INSERT" in grant_str:
                perms["INSERT"] = True
            if "CREATE" in grant_str:
                perms["CREATE"] = True

        return perms

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
