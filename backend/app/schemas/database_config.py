"""Request and response schemas for database configuration endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.database_config import DatabaseConfig, DatabaseConfigType


@dataclass(frozen=True)
class CreateDatabaseConfigRequest:
    """Represents the payload used to create a database configuration."""

    name: str
    database_type: str
    host: str
    port: int
    username: str
    password: str | None
    purpose: str
    aws_connection_id: int | None = None
    secret_arn: str | None = None
    secret_name: str | None = None
    provisioning_config: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "CreateDatabaseConfigRequest":
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        name = payload.get("name")
        database_type = payload.get("database_type")
        host = payload.get("host")
        port = payload.get("port")
        username = payload.get("username")
        password = payload.get("password")
        purpose = payload.get("purpose", "SOURCE")
        aws_connection_id = payload.get("aws_connection_id")
        secret_arn = payload.get("secret_arn")
        secret_name = payload.get("secret_name")
        provisioning_config = payload.get("provisioning_config")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Name is required.")
        if not isinstance(database_type, str) or not database_type.strip():
            raise ValueError("Database type is required.")
        if not isinstance(host, str) or not host.strip():
            raise ValueError("Host is required.")
        if not isinstance(port, int) or port < 1:
            raise ValueError("Port must be a positive integer.")
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Username is required.")
        
        normalized_purpose = purpose.strip().upper()
        if normalized_purpose == "SOURCE":
            if not isinstance(password, str) or not password.strip():
                raise ValueError("Password is required for source database configurations.")
        else:
            if password is not None and (not isinstance(password, str) or not password.strip()):
                password = None

        normalized_database_type = database_type.strip().upper()
        if normalized_database_type not in DatabaseConfigType.VALUES:
            raise ValueError("Database type must be one of: POSTGRESQL, MYSQL, ORACLE, SQL_SERVER.")

        if aws_connection_id is not None:
            try:
                aws_connection_id = int(aws_connection_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("aws_connection_id must be an integer.") from exc

        return cls(
            name=name.strip(),
            database_type=normalized_database_type,
            host=host.strip(),
            port=port,
            username=username.strip(),
            password=password.strip() if password else None,
            purpose=normalized_purpose,
            aws_connection_id=aws_connection_id,
            secret_arn=secret_arn.strip() if isinstance(secret_arn, str) and secret_arn.strip() else None,
            secret_name=secret_name.strip() if isinstance(secret_name, str) and secret_name.strip() else None,
            provisioning_config=provisioning_config if isinstance(provisioning_config, str) else None,
        )


@dataclass(frozen=True)
class DatabaseConfigResponse:
    """Represents the structured JSON returned by database config endpoints."""

    id: int
    name: str
    database_type: str
    host: str
    port: int
    username: str
    purpose: str
    aws_connection_id: int | None
    secret_arn: str | None
    secret_name: str | None
    provisioning_config: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "database_type": self.database_type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "purpose": self.purpose,
            "aws_connection_id": self.aws_connection_id,
            "secret_arn": self.secret_arn,
            "secret_name": self.secret_name,
            "provisioning_config": self.provisioning_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_model(cls, config: DatabaseConfig) -> "DatabaseConfigResponse":
        return cls(
            id=config.id,
            name=config.name,
            database_type=config.database_type,
            host=config.host,
            port=config.port,
            username=config.username,
            purpose=config.purpose,
            aws_connection_id=config.aws_connection_id,
            secret_arn=config.secret_arn,
            secret_name=config.secret_name,
            provisioning_config=config.provisioning_config,
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else "",
        )


@dataclass(frozen=True)
class DeleteDatabaseConfigResponse:
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"message": self.message}
