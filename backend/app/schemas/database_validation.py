"""Response schemas for database validation endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationCheck:
    """A single step in the validation pipeline."""

    step: str
    label: str
    passed: bool
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "step": self.step,
            "label": self.label,
            "passed": self.passed,
        }
        if self.detail:
            d["detail"] = self.detail
        return d


@dataclass(frozen=True)
class SourceValidationResponse:
    """Full validation result for a SOURCE database."""

    connection: str  # "success" | "failed"
    database: str
    selected_table: str | None = None
    columns: list[str] = field(default_factory=list)
    sample_rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int | None = None
    tables: list[str] = field(default_factory=list)
    checks: list[ValidationCheck] = field(default_factory=list)
    masked_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connection": self.connection,
            "database": self.database,
            "selectedTable": self.selected_table,
            "columns": self.columns,
            "sampleRows": self.sample_rows,
            "rowCount": self.row_count,
            "tables": self.tables,
            "checks": [c.to_dict() for c in self.checks],
            "maskedColumns": self.masked_columns,
        }


@dataclass(frozen=True)
class DestinationValidationResponse:
    """Validation result for a DESTINATION database (no table data)."""

    connection: str
    database_exists: bool
    write_permission: bool
    read_permission: bool
    checks: list[ValidationCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connection": self.connection,
            "databaseExists": self.database_exists,
            "writePermission": self.write_permission,
            "readPermission": self.read_permission,
            "checks": [c.to_dict() for c in self.checks],
        }
