"""Request and response schemas for notification endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.models.notification import NotificationConfig, Notification


@dataclass(frozen=True)
class CreateNotificationConfigRequest:
    """Represents the payload required to create a notification configuration."""

    user_id: str
    notification_type: str
    email_address: str | None = None
    slack_webhook_url: str | None = None
    slack_channel: str | None = None
    webhook_url: str | None = None
    webhook_headers: dict[str, str] | None = None
    subscribed_events: list[str] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "CreateNotificationConfigRequest":
        """Convert raw JSON into a validated creation request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        user_id = payload.get("user_id")
        notification_type = payload.get("notification_type")
        email_address = payload.get("email_address")
        slack_webhook_url = payload.get("slack_webhook_url")
        slack_channel = payload.get("slack_channel")
        webhook_url = payload.get("webhook_url")
        webhook_headers = payload.get("webhook_headers")
        subscribed_events = payload.get("subscribed_events")

        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id is required and must be a string.")
        if not notification_type or not isinstance(notification_type, str):
            raise ValueError("notification_type is required and must be a string.")

        from app.models.notification import NotificationType
        if notification_type not in NotificationType.VALUES:
            raise ValueError(f"notification_type must be one of: {', '.join(NotificationType.VALUES)}")

        return cls(
            user_id=user_id,
            notification_type=notification_type,
            email_address=email_address,
            slack_webhook_url=slack_webhook_url,
            slack_channel=slack_channel,
            webhook_url=webhook_url,
            webhook_headers=webhook_headers if isinstance(webhook_headers, dict) else None,
            subscribed_events=subscribed_events if isinstance(subscribed_events, list) else None,
        )


@dataclass(frozen=True)
class SendNotificationRequest:
    """Represents the payload required to send a notification."""

    event_type: str
    subject: str
    body: str
    migration_id: int | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "SendNotificationRequest":
        """Convert raw JSON into a validated send request object."""
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        event_type = payload.get("event_type")
        subject = payload.get("subject")
        body = payload.get("body")
        migration_id = payload.get("migration_id")
        payload_data = payload.get("payload")

        if not event_type or not isinstance(event_type, str):
            raise ValueError("event_type is required and must be a string.")
        if not subject or not isinstance(subject, str):
            raise ValueError("subject is required and must be a string.")
        if not body or not isinstance(body, str):
            raise ValueError("body is required and must be a string.")

        try:
            if migration_id is not None:
                migration_id = int(migration_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("migration_id must be an integer.") from exc

        return cls(
            event_type=event_type,
            subject=subject,
            body=body,
            migration_id=migration_id,
            payload=payload_data if isinstance(payload_data, dict) else None,
        )


@dataclass(frozen=True)
class NotificationConfigResponse:
    """Represents the structured JSON returned by notification config endpoints."""

    id: int
    user_id: str
    notification_type: str
    email_address: str | None
    slack_webhook_url: str | None
    slack_channel: str | None
    webhook_url: str | None
    webhook_headers: dict[str, str] | None
    subscribed_events: list[str] | None
    enabled: bool
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "email_address": self.email_address,
            "slack_webhook_url": self.slack_webhook_url,
            "slack_channel": self.slack_channel,
            "webhook_url": self.webhook_url,
            "webhook_headers": self.webhook_headers,
            "subscribed_events": self.subscribed_events,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_model(cls, config: NotificationConfig) -> "NotificationConfigResponse":
        """Build a response DTO from a persisted notification config."""
        return cls(
            id=config.id,
            user_id=config.user_id,
            notification_type=config.notification_type,
            email_address=config.email_address,
            slack_webhook_url=config.slack_webhook_url,
            slack_channel=config.slack_channel,
            webhook_url=config.webhook_url,
            webhook_headers=json.loads(config.webhook_headers) if config.webhook_headers else None,
            subscribed_events=json.loads(config.subscribed_events) if config.subscribed_events else None,
            enabled=config.enabled,
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else "",
        )


@dataclass(frozen=True)
class NotificationResponse:
    """Represents a notification response."""

    id: int
    notification_config_id: int | None
    migration_id: int | None
    event_type: str
    notification_type: str
    subject: str | None
    body: str | None
    payload: dict[str, Any] | None
    status: str
    error_message: str | None
    retry_count: int
    sent_at: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response object into a JSON-safe dictionary."""
        return {
            "id": self.id,
            "notification_config_id": self.notification_config_id,
            "migration_id": self.migration_id,
            "event_type": self.event_type,
            "notification_type": self.notification_type,
            "subject": self.subject,
            "body": self.body,
            "payload": self.payload,
            "status": self.status,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "sent_at": self.sent_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_model(cls, notification: Notification) -> "NotificationResponse":
        """Build a response DTO from a persisted notification."""
        return cls(
            id=notification.id,
            notification_config_id=notification.notification_config_id,
            migration_id=notification.migration_id,
            event_type=notification.event_type,
            notification_type=notification.notification_type,
            subject=notification.subject,
            body=notification.body,
            payload=json.loads(notification.payload) if notification.payload else None,
            status=notification.status,
            error_message=notification.error_message,
            retry_count=notification.retry_count,
            sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
            created_at=notification.created_at.isoformat() if notification.created_at else "",
        )
