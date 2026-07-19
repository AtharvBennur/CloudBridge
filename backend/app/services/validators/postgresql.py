"""PostgreSQL database validator using psycopg2."""

from __future__ import annotations

import logging
from typing import Any

import psycopg2
import psycopg2.extras

from app.services.validators.base import BaseDatabaseValidator
from app.services.validators.sensitive_masker import is_binary_column

logger = logging.getLogger(__name__)

# System schemas to exclude from table discovery
_SYSTEM_SCHEMAS = frozenset({"pg_catalog", "information_schema"})


class PostgreSQLValidator(BaseDatabaseValidator):
    """Validates PostgreSQL connections, permissions, and discovers tables."""

    engine = "POSTGRESQL"

    def connect(self) -> None:
        self._connection = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            dbname=self.database_name or "postgres",
            connect_timeout=self.timeout,
            options=f"-c statement_timeout={self.timeout * 1000}",
        )
        self._connection.autocommit = True
        logger.info("PostgreSQL connection established to %s:%s/%s", self.host, self.port, self.database_name)

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
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.database_name,))
            return cur.fetchone() is not None

    def discover_tables(self) -> list[str]:
        with self._connection.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            return [row[0] for row in cur.fetchall()]

    def validate_permissions(self) -> dict[str, bool]:
        perms: dict[str, bool] = {}
        with self._connection.cursor() as cur:
            # SELECT on all tables
            cur.execute(
                "SELECT has_database_privilege(%s, 'CREATE')",
                (self.database_name or "postgres",),
            )
            perms["CREATE"] = cur.fetchone()[0]

            # Check SELECT and INSERT on first user table
            tables = self.discover_tables()
            if tables:
                table = tables[0]
                cur.execute(
                    "SELECT has_table_privilege(%s, 'SELECT'), has_table_privilege(%s, 'INSERT')",
                    (table, table),
                )
                row = cur.fetchone()
                perms["SELECT"] = row[0]
                perms["INSERT"] = row[1]
            else:
                perms["SELECT"] = True
                perms["INSERT"] = True

        return perms

    def fetch_sample_rows(self, table: str, limit: int = 5) -> tuple[list[str], list[dict[str, Any]]]:
        with self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Get column info to exclude binary columns
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            all_columns = cur.fetchall()

            safe_columns = [
                col_name for col_name, data_type in all_columns
                if not is_binary_column(data_type)
            ]

            if not safe_columns:
                return [], []

            # Fetch sample rows
            col_list = ", ".join(f'"{c}"' for c in safe_columns)
            cur.execute(f'SELECT {col_list} FROM "{table}" LIMIT %s', (limit,))
            rows = cur.fetchall()

            result_rows = []
            for row in rows:
                row_dict = {col: row[col] for col in safe_columns}
                result_rows.append(row_dict)

            return safe_columns, result_rows

    def get_table_row_count(self, table: str) -> int | None:
        try:
            with self._connection.cursor() as cur:
                cur.execute(
                    "SELECT reltuples::bigint FROM pg_class WHERE relname = %s",
                    (table,),
                )
                row = cur.fetchone()
                if row and row[0] >= 0:
                    return int(row[0])
        except Exception:
            pass
        return None
