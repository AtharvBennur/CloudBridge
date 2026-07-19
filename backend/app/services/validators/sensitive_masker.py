"""Sensitive data masking for database validation preview.

Detects sensitive columns by name pattern and masks values before
returning sample data to the frontend. Never exposes passwords,
tokens, PII, or financial data in plain text.
"""

from __future__ import annotations

import re
from typing import Any

# ── Sensitive column name patterns ───────────────────────────────────────────
SENSITIVE_PATTERNS: frozenset[str] = frozenset({
    "password", "pwd", "secret", "token", "apikey", "api_key",
    "email", "phone", "mobile", "contact", "ssn", "aadhaar", "pan",
    "credit", "card", "cvv", "otp", "dob", "salary", "address",
    "license", "passport",
})

# Columns that are ALWAYS fully redacted (never show partial values)
FULLY_REDACTED_PATTERNS: frozenset[str] = frozenset({
    "password", "pwd", "secret", "token", "apikey", "api_key",
    "cvv", "otp", "ssn", "aadhaar", "pan", "passport",
})

# Email-like pattern
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Phone-like pattern (digits, possibly with country code prefix)
_PHONE_RE = re.compile(r"^[\d+\-\s()]{7,20}$")

# Binary / BLOB column types to exclude entirely
BINARY_TYPES: frozenset[str] = frozenset({
    "bytea", "blob", "clob", "binary", "varbinary", "image",
    "longblob", "mediumblob", "tinyblob", "raw", "long raw", "bfile",
    "nclob", "bfile", "long",
})


def should_mask_column(column_name: str) -> bool:
    """Return True if the column name matches any sensitive pattern."""
    normalised = column_name.lower().replace("-", "_").replace(" ", "_")
    for pattern in SENSITIVE_PATTERNS:
        if pattern in normalised:
            return True
    return False


def is_binary_column(data_type: str) -> bool:
    """Return True if the data type is a binary/blob type."""
    return data_type.lower().strip() in BINARY_TYPES


def _is_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value))


def _is_phone(value: str) -> bool:
    digits = re.sub(r"[^\d]", "", value)
    return len(digits) >= 7 and bool(_PHONE_RE.match(value))


def _mask_email(value: str) -> str:
    """john@gmail.com -> j***@gmail.com"""
    local, domain = value.rsplit("@", 1)
    if len(local) <= 1:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def _mask_phone(value: str) -> str:
    """9876543210 -> 98******10"""
    digits = re.sub(r"[^\d]", "", value)
    if len(digits) <= 4:
        return "*" * len(digits)
    return f"{digits[:2]}{'*' * (len(digits) - 4)}{digits[-2:]}"


def _mask_numeric(value: Any) -> str:
    """95000 -> *****"""
    return "*****"


def _mask_generic(value: str) -> str:
    """John Doe -> ********"""
    return "********"


def mask_value(column_name: str, value: Any) -> str:
    """Mask a single value based on its column name and content.

    Returns the masked string representation.
    """
    if value is None:
        return "NULL"

    normalised = column_name.lower().replace("-", "_").replace(" ", "_")

    # Fully redacted columns: never show any partial data
    for pattern in FULLY_REDACTED_PATTERNS:
        if pattern in normalised:
            return "********"

    str_value = str(value)

    # If it looks like an email, mask as email
    if _is_email(str_value):
        return _mask_email(str_value)

    # If it looks like a phone number, mask as phone
    if _is_phone(str_value) and any(p in normalised for p in ("phone", "mobile", "contact")):
        return _mask_phone(str_value)

    # Numeric sensitive columns (salary, credit, card, cvv)
    numeric_patterns = {"salary", "credit", "card", "cvv"}
    if any(p in normalised for p in numeric_patterns):
        return _mask_numeric(value)

    # Default: generic mask
    return _mask_generic(str_value)


def mask_row(
    row: dict[str, Any],
    column_types: dict[str, str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Mask sensitive values in a row dict.

    Returns (masked_row, list_of_masked_column_names).
    """
    masked_row: dict[str, Any] = {}
    masked_columns: list[str] = []

    for col, value in row.items():
        if should_mask_column(col):
            masked_row[col] = mask_value(col, value)
            masked_columns.append(col)
        else:
            masked_row[col] = value

    return masked_row, masked_columns
