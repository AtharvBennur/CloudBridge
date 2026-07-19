"""Oracle database validator using python-oracledb (thin mode)."""

from __future__ import annotations

import logging
from typing import Any

import oracledb

from app.services.validators.base import BaseDatabaseValidator

logger = logging.getLogger(__name__)

# Oracle binary/LOB column types
_ORACLE_BINARY_TYPES = frozenset({
    "blob", "clob", "nclob", "bfile", "raw", "long raw", "long",
})

# Oracle system schemas to exclude
_ORACLE_SYSTEM_SCHEMAS = frozenset({
    "SYS", "SYSTEM", "DBSNMP", "APPQOSSYS", "OUTLN", "XS$NULL",
    "ORACLE_OCM", "FLOWS_FILES", "APEX_PUBLIC_USER", "APEX_040000",
    "APEX_040200", "APEX_030200", "APEX_030100", "APEX_050000",
    "CTXSYS", "MDSYS", "OLAPSYS", "ORDSYS", "ORDPLUGINS",
    "OJVMSYS", "LBACSYS", "WMSYS", "XDB", "ANONYMOUS",
    "SCOTT", "HR", "PM", "SH", "OE", "IX",
})


class OracleValidator(BaseDatabaseValidator):
    """Validates Oracle connections, permissions, and discovers tables.

    Uses thin mode by default (no Oracle Instant Client required).
    """

    engine = "ORACLE"

    def connect(self) -> None:
        # Thin mode by default - no Instant Client needed
        oracledb.init_oracle_client() if False else None  # Skip thick mode

        dsn = f"{self.host}:{self.port}/{self.database_name}" if self.database_name else f"{self.host}:{self.port}"

        self._connection = oracledb.connect(
            user=self.username,
            password=self.password,
            dsn=dsn,
        )
        logger.info("Oracle connection established to %s:%s/%s", self.host, self.port, self.database_name)

    def close(self) -> None:
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def validate_connection(self) -> bool:
        with self._connection.cursor() as cur:
            cur.execute("SELECT 1 FROM DUAL")
            return True

    def database_exists(self) -> bool:
        # In Oracle, the "database" is the service/SID we connected to.
        # If we connected successfully, the database exists.
        try:
            with self._connection.cursor() as cur:
                cur.execute("SELECT 1 FROM V$DATABASE WHERE ROWNUM <= 1")
                return True
        except Exception:
            # Fallback: if we're connected, the database exists
            return self._connection is not None

    def discover_tables(self) -> list[str]:
        with self._connection.cursor() as cur:
            cur.execute("""
                SELECT TABLE_NAME
                FROM ALL_TABLES
                WHERE OWNER = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')
                ORDER BY TABLE_NAME
            """)
            return [row[0] for row in cur.fetchall()]

    def validate_permissions(self) -> dict[str, bool]:
        perms: dict[str, bool] = {"SELECT": False, "INSERT": False, "CREATE": False}

        with self._connection.cursor() as cur:
            # Check CREATE TABLE privilege
            cur.execute("""
                SELECT PRIVILEGE FROM SESSION_PRIVS
                WHERE PRIVILEGE IN ('CREATE TABLE', 'CREATE ANY TABLE')
            """)
            perms["CREATE"] = cur.fetchone() is not None

            # Check SELECT and INSERT on first user table
            tables = self.discover_tables()
            if tables:
                table = tables[0]
                cur.execute("""
                    SELECT PRIVILEGE FROM USER_TAB_PRIVS
                    WHERE TABLE_NAME = :1 AND PRIVILEGE IN ('SELECT', 'INSERT')
                """, [table])
                found_privs = {row[0] for row in cur.fetchall()}
                perms["SELECT"] = "SELECT" in found_privs
                perms["INSERT"] = "INSERT" in found_privs
            else:
                perms["SELECT"] = True
                perms["INSERT"] = True

        return perms

    def fetch_sample_rows(self, table: str, limit: int = 5) -> tuple[list[str], list[dict[str, Any]]]:
        with self._connection.cursor() as cur:
            # Get column info to exclude binary/LOB columns
            cur.execute("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM ALL_TAB_COLUMNS
                WHERE TABLE_NAME = :1
                  AND OWNER = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')
                ORDER BY COLUMN_ID
            """, [table])
            all_columns = cur.fetchall()

            safe_columns = [
                col_name for col_name, data_type in all_columns
                if data_type.lower() not in _ORACLE_BINARY_TYPES
            ]

            if not safe_columns:
                return [], []

            col_list = ", ".join(f'"{c}"' for c in safe_columns)
            cur.execute(f'SELECT {col_list} FROM "{table}" WHERE ROWNUM <= :1', [limit])

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
                    SELECT NUM_ROWS
                    FROM ALL_TABLES
                    WHERE TABLE_NAME = :1
                      AND OWNER = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')
                """, [table])
                row = cur.fetchone()
                if row and row[0] is not None:
                    return int(row[0])
        except Exception:
            pass
        return None
