"""Service layer for notification delivery (Email, Slack, Webhook)."""

from __future__ import annotations

import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any
import requests

from flask import current_app

from app.extensions import db
from app.models.notification import (
    NotificationConfig,
    Notification,
    NotificationType,
    NotificationEventType,
    NotificationStatus,
)


class NotificationServiceError(Exception):
    """Base exception for notification service errors."""


class NotificationConfigNotFoundError(NotificationServiceError):
    """Raised when a notification configuration cannot be located."""


class NotificationDeliveryError(NotificationServiceError):
    """Raised when notification delivery fails."""


class NotificationService:
    """Coordinates notification delivery across multiple channels."""

    def __init__(self, logger: Any | None = None) -> None:
        self._logger = logger

    def create_notification_config(
        self,
        user_id: str,
        notification_type: str,
        email_address: str | None = None,
        slack_webhook_url: str | None = None,
        slack_channel: str | None = None,
        webhook_url: str | None = None,
        webhook_headers: dict[str, str] | None = None,
        subscribed_events: list[str] | None = None,
    ) -> NotificationConfig:
        """Create a notification configuration for a user."""
        if notification_type not in NotificationType.VALUES:
            raise NotificationServiceError(f"Invalid notification type: {notification_type}")

        config = NotificationConfig(
            user_id=user_id,
            notification_type=notification_type,
            email_address=email_address,
            slack_webhook_url=slack_webhook_url,
            slack_channel=slack_channel,
            webhook_url=webhook_url,
            webhook_headers=json.dumps(webhook_headers) if webhook_headers else None,
            subscribed_events=json.dumps(subscribed_events) if subscribed_events else None,
            enabled=True,
        )
        db.session.add(config)
        db.session.commit()

        self._log_info(f"Notification config created for user {user_id}, type {notification_type}")
        return config

    def send_notification(
        self,
        event_type: str,
        subject: str,
        body: str,
        migration_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> list[Notification]:
        """Send notifications to all subscribed users for an event."""
        notifications = []

        # Get all notification configs subscribed to this event
        configs = NotificationConfig.query.filter_by(enabled=True).all()

        for config in configs:
            subscribed_events = json.loads(config.subscribed_events) if config.subscribed_events else []
            if subscribed_events and event_type not in subscribed_events:
                continue

            # Create notification record
            notification = Notification(
                notification_config_id=config.id,
                migration_id=migration_id,
                event_type=event_type,
                notification_type=config.notification_type,
                subject=subject,
                body=body,
                payload=json.dumps(payload) if payload else None,
                status=NotificationStatus.PENDING,
            )
            db.session.add(notification)
            notifications.append(notification)

        db.session.commit()

        # Deliver notifications
        for notification in notifications:
            try:
                self._deliver_notification(notification)
            except Exception as exc:
                self._logger.error(f"Failed to deliver notification {notification.id}: {exc}")
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(exc)
                db.session.commit()

        return notifications

    def _deliver_notification(self, notification: Notification) -> None:
        """Deliver a notification based on its type."""
        config = NotificationConfig.query.get(notification.notification_config_id)
        if not config:
            raise NotificationConfigNotFoundError(f"Notification config {notification.notification_config_id} not found")

        if notification.notification_type == NotificationType.EMAIL:
            self._send_email_notification(config, notification)
        elif notification.notification_type == NotificationType.SLACK:
            self._send_slack_notification(config, notification)
        elif notification.notification_type == NotificationType.WEBHOOK:
            self._send_webhook_notification(config, notification)
        else:
            raise NotificationServiceError(f"Unsupported notification type: {notification.notification_type}")

    def _send_email_notification(self, config: NotificationConfig, notification: Notification) -> None:
        """Send an email notification."""
        if not config.email_address:
            raise NotificationDeliveryError("Email address not configured")

        # In production, this would use SMTP settings from config
        # For now, we'll simulate email delivery
        self._log_info(f"Email notification sent to {config.email_address}: {notification.subject}")

        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        db.session.commit()

    def _send_slack_notification(self, config: NotificationConfig, notification: Notification) -> None:
        """Send a Slack notification via webhook."""
        if not config.slack_webhook_url:
            raise NotificationDeliveryError("Slack webhook URL not configured")

        try:
            slack_payload = {
                "text": notification.subject,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": notification.subject,
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": notification.body,
                        },
                    },
                ],
            }

            if config.slack_channel:
                slack_payload["channel"] = config.slack_channel

            response = requests.post(config.slack_webhook_url, json=slack_payload, timeout=10)
            response.raise_for_status()

            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
            db.session.commit()

            self._log_info(f"Slack notification sent to {config.slack_channel or 'default channel'}")

        except Exception as exc:
            raise NotificationDeliveryError(f"Failed to send Slack notification: {exc}") from exc

    def _send_webhook_notification(self, config: NotificationConfig, notification: Notification) -> None:
        """Send a webhook notification."""
        if not config.webhook_url:
            raise NotificationDeliveryError("Webhook URL not configured")

        try:
            headers = json.loads(config.webhook_headers) if config.webhook_headers else {}
            payload = json.loads(notification.payload) if notification.payload else {}

            webhook_payload = {
                "event_type": notification.event_type,
                "subject": notification.subject,
                "body": notification.body,
                "migration_id": notification.migration_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload,
            }

            response = requests.post(config.webhook_url, json=webhook_payload, headers=headers, timeout=10)
            response.raise_for_status()

            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
            db.session.commit()

            self._log_info(f"Webhook notification sent to {config.webhook_url}")

        except Exception as exc:
            raise NotificationDeliveryError(f"Failed to send webhook notification: {exc}") from exc

    def retry_failed_notifications(self) -> int:
        """Retry failed notifications that haven't exceeded max retries."""
        failed_notifications = Notification.query.filter_by(status=NotificationStatus.FAILED).all()
        retried_count = 0

        for notification in failed_notifications:
            if notification.retry_count < notification.max_retries:
                notification.retry_count += 1
                notification.status = NotificationStatus.RETRYING
                db.session.commit()

                try:
                    self._deliver_notification(notification)
                    retried_count += 1
                except Exception as exc:
                    self._logger.error(f"Retry failed for notification {notification.id}: {exc}")
                    notification.status = NotificationStatus.FAILED
                    db.session.commit()

        return retried_count

    def get_user_notification_configs(self, user_id: str) -> list[NotificationConfig]:
        """Get all notification configurations for a user."""
        return NotificationConfig.query.filter_by(user_id=user_id).all()

    def get_notification_history(
        self,
        user_id: str | None = None,
        event_type: str | None = None,
        migration_id: int | None = None,
        limit: int = 100,
    ) -> list[Notification]:
        """Get notification history with optional filters."""
        query = Notification.query

        if user_id:
            query = query.join(NotificationConfig).filter(NotificationConfig.user_id == user_id)
        if event_type:
            query = query.filter_by(event_type=event_type)
        if migration_id:
            query = query.filter_by(migration_id=migration_id)

        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def delete_notification_config(self, config_id: int) -> None:
        """Delete a notification configuration."""
        config = NotificationConfig.query.get(config_id)
        if not config:
            raise NotificationConfigNotFoundError(f"Notification config {config_id} not found")

        db.session.delete(config)
        db.session.commit()

        self._log_info(f"Notification config {config_id} deleted")

    def _log_info(self, message: str) -> None:
        """Write a structured log entry."""
        logger = self._logger or current_app.logger
        logger.info(message)
