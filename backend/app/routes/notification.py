"""
Purpose:
This file contains the notification HTTP endpoints for Email, Slack, and Webhook delivery.

Why:
Blueprints keep the API surface organized and allow the service layer to remain focused on business logic.

Architecture:
Notification Blueprint
↓
Notification Service
↓
Notification Model
"""

from flask import Blueprint, jsonify, request

from app.exceptions.notification import NotificationConfigNotFoundError, NotificationDeliveryError, NotificationServiceError, NotificationValidationError
from app.middleware.auth import login_required
from app.schemas.notification import CreateNotificationConfigRequest, SendNotificationRequest, NotificationConfigResponse, NotificationResponse
from app.services.notification_service import NotificationService

notification_bp = Blueprint("notification", __name__, url_prefix="/notifications")
notification_service = NotificationService()


@notification_bp.errorhandler(NotificationValidationError)
def handle_validation_error(error: NotificationValidationError):
    """Return a validation error response for invalid notification payloads."""
    return jsonify({"error": {"message": error.message}}), 400


@notification_bp.errorhandler(NotificationConfigNotFoundError)
def handle_not_found_error(error: NotificationConfigNotFoundError):
    """Return a not-found error response when a notification config is missing."""
    return jsonify({"error": {"message": error.message}}), 404


@notification_bp.errorhandler(NotificationDeliveryError)
def handle_delivery_error(error: NotificationDeliveryError):
    """Return a delivery error response when notification delivery fails."""
    return jsonify({"error": {"message": error.message}}), 502


@notification_bp.errorhandler(NotificationServiceError)
def handle_notification_error(error: NotificationServiceError):
    """Return a generic response for notification service failures."""
    return jsonify({"error": {"message": error.message}}), 400


@notification_bp.post("/config")
@login_required
def create_notification_config():
    """Create a notification configuration for a user."""
    payload = request.get_json(silent=True)
    try:
        create_request = CreateNotificationConfigRequest.from_payload(payload)
        config = notification_service.create_notification_config(
            user_id=create_request.user_id,
            notification_type=create_request.notification_type,
            email_address=create_request.email_address,
            slack_webhook_url=create_request.slack_webhook_url,
            slack_channel=create_request.slack_channel,
            webhook_url=create_request.webhook_url,
            webhook_headers=create_request.webhook_headers,
            subscribed_events=create_request.subscribed_events,
        )
        return jsonify(NotificationConfigResponse.from_model(config).to_dict()), 201
    except NotificationServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@notification_bp.get("/config/<int:config_id>")
@login_required
def get_notification_config(config_id: int):
    """Get a notification configuration by ID."""
    from app.models.notification import NotificationConfig
    
    config = NotificationConfig.query.get(config_id)
    if not config:
        return jsonify({"error": {"message": "Notification configuration not found"}}), 404
    
    return jsonify(NotificationConfigResponse.from_model(config).to_dict()), 200


@notification_bp.get("/config/user/<user_id>")
@login_required
def get_user_notification_configs(user_id: str):
    """Get all notification configurations for a user."""
    try:
        configs = notification_service.get_user_notification_configs(user_id)
        return jsonify([NotificationConfigResponse.from_model(config).to_dict() for config in configs]), 200
    except NotificationServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@notification_bp.delete("/config/<int:config_id>")
@login_required
def delete_notification_config(config_id: int):
    """Delete a notification configuration."""
    try:
        notification_service.delete_notification_config(config_id)
        return jsonify({"message": "Notification configuration deleted successfully"}), 200
    except NotificationServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@notification_bp.post("/send")
@login_required
def send_notification():
    """Send a notification to all subscribed users."""
    payload = request.get_json(silent=True)
    try:
        send_request = SendNotificationRequest.from_payload(payload)
        notifications = notification_service.send_notification(
            event_type=send_request.event_type,
            subject=send_request.subject,
            body=send_request.body,
            migration_id=send_request.migration_id,
            payload=send_request.payload,
        )
        return jsonify({
            "message": "Notifications sent",
            "count": len(notifications),
            "notifications": [NotificationResponse.from_model(n).to_dict() for n in notifications],
        }), 200
    except NotificationServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@notification_bp.post("/retry-failed")
@login_required
def retry_failed_notifications():
    """Retry failed notifications."""
    try:
        retried_count = notification_service.retry_failed_notifications()
        return jsonify({"message": f"Retried {retried_count} failed notifications"}), 200
    except NotificationServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@notification_bp.get("/history")
@login_required
def get_notification_history():
    """Get notification history with optional filters."""
    user_id = request.args.get("user_id")
    event_type = request.args.get("event_type")
    migration_id = request.args.get("migration_id", type=int)
    limit = request.args.get("limit", 100, type=int)

    try:
        notifications = notification_service.get_notification_history(
            user_id=user_id,
            event_type=event_type,
            migration_id=migration_id,
            limit=limit,
        )
        return jsonify([NotificationResponse.from_model(n).to_dict() for n in notifications]), 200
    except NotificationServiceError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400


@notification_bp.get("/history/<int:notification_id>")
@login_required
def get_notification(notification_id: int):
    """Get a specific notification by ID."""
    from app.models.notification import Notification
    
    notification = Notification.query.get(notification_id)
    if not notification:
        return jsonify({"error": {"message": "Notification not found"}}), 404
    
    return jsonify(NotificationResponse.from_model(notification).to_dict()), 200
