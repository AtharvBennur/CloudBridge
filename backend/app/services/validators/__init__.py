"""Validator factory — returns the correct engine-specific validator.

Usage:
    from app.services.validators import get_validator

    with get_validator("POSTGRESQL", host, port, user, pwd, db) as v:
        tables = v.discover_tables()
"""

from __future__ import annotations

from app.services.validators.base import BaseDatabaseValidator


def get_validator(
    engine: str,
    host: str,
    port: int,
    username: str,
    password: str,
    database_name: str | None = None,
    timeout: int = 5,
) -> BaseDatabaseValidator:
    """Return an engine-specific validator instance.

    Raises ValueError if the engine is not supported.
    """
    normalized = engine.strip().upper()

    if normalized == "POSTGRESQL":
        from app.services.validators.postgresql import PostgreSQLValidator
        return PostgreSQLValidator(host, port, username, password, database_name, timeout)

    if normalized == "MYSQL":
        from app.services.validators.mysql import MySQLValidator
        return MySQLValidator(host, port, username, password, database_name, timeout)

    if normalized == "SQL_SERVER":
        from app.services.validators.sqlserver import SQLServerValidator
        return SQLServerValidator(host, port, username, password, database_name, timeout)

    if normalized == "ORACLE":
        from app.services.validators.oracle import OracleValidator
        return OracleValidator(host, port, username, password, database_name, timeout)

    raise ValueError(f"Unsupported database engine: {engine!r}. Supported: POSTGRESQL, MYSQL, SQL_SERVER, ORACLE.")


__all__ = [
    "BaseDatabaseValidator",
    "get_validator",
]
