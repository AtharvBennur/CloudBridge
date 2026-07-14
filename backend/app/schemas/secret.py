"""Validation DTOs for customer Secrets Manager operations."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SecretWriteRequest:
    name: str
    value: dict[str, Any]
    description: str = "CloudBridge managed database credential"

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "SecretWriteRequest":
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        name, value = payload.get("name"), payload.get("value")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Secret name is required.")
        if not isinstance(value, dict) or not value:
            raise ValueError("Secret value must be a non-empty JSON object.")
        description = payload.get("description", cls.description)
        if not isinstance(description, str):
            raise ValueError("Secret description must be a string.")
        return cls(name=name.strip(), value=value, description=description.strip())


@dataclass(frozen=True)
class SecretReferenceRequest:
    secret_id: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "SecretReferenceRequest":
        if not isinstance(payload, dict) or not isinstance(payload.get("secret_id"), str) or not payload["secret_id"].strip():
            raise ValueError("secret_id is required.")
        return cls(secret_id=payload["secret_id"].strip())
