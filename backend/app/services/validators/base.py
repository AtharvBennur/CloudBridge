"""Abstract base class for database engine validators.

Defines the contract that all engine-specific validators must implement.
Uses context manager pattern for safe connection cleanup.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseDatabaseValidator(ABC):
    """Base interface for all database engine validators.

    Usage:
        with get_validator("POSTGRESQL", host, port, user, pwd, db) as validator:
            validator.validate_connection()
            validator.discover_tables()
            validator.fetch_sample_rows("users")
    """

    engine: str  # POSTGRESQL, MYSQL, SQL_SERVER, ORACLE

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        database_name: str | None = None,
        timeout: int = 5,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database_name = database_name
        self.timeout = timeout
        self._connection: Any = None

    # ── Context manager ──────────────────────────────────────────────────
    def __enter__(self) -> "BaseDatabaseValidator":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    # ── Abstract interface ───────────────────────────────────────────────
    @abstractmethod
    def connect(self) -> None:
        """Open a database connection. Must raise on failure."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the database connection. Must be safe to call multiple times."""
        ...

    @abstractmethod
    def validate_connection(self) -> bool:
        """Return True if credentials are valid (e.g. SELECT 1)."""
        ...

    @abstractmethod
    def database_exists(self) -> bool:
        """Return True if the target database/schema exists."""
        ...

    @abstractmethod
    def discover_tables(self) -> list[str]:
        """Return user tables, excluding system schemas."""
        ...

    @abstractmethod
    def validate_permissions(self) -> dict[str, bool]:
        """Return a dict of privilege -> bool, e.g. {'SELECT': True, 'INSERT': True}."""
        ...

    @abstractmethod
    def fetch_sample_rows(self, table: str, limit: int = 5) -> tuple[list[str], list[dict[str, Any]]]:
        """Return (columns, rows) for up to `limit` rows.

        Binary/BLOB columns must be excluded.
        Each row is a dict mapping column_name -> value.
        """
        ...

    @abstractmethod
    def get_table_row_count(self, table: str) -> int | None:
        """Return an approximate row count if inexpensive, else None."""
        ...

    # ── Shared helpers ───────────────────────────────────────────────────
    @property
    def is_connected(self) -> bool:
        return self._connection is not None
