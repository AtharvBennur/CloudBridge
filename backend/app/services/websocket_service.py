"""Service layer for WebSocket real-time communication."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from flask import current_app, has_app_context, request
from flask_socketio import emit, join_room, leave_room

from app.extensions import socketio


def _get_logger() -> logging.Logger:
    if has_app_context():
        return current_app.logger
    return logging.getLogger("app.websocket")


class WebSocketService:
    """Coordinates WebSocket connections and real-time event broadcasting."""

    @staticmethod
    def join_migration_room(migration_id: int) -> None:
        room = f"migration_{migration_id}"
        join_room(room)
        _get_logger().info(f"Client joined room: {room}")

    @staticmethod
    def leave_migration_room(migration_id: int) -> None:
        room = f"migration_{migration_id}"
        leave_room(room)
        _get_logger().info(f"Client left room: {room}")

    @staticmethod
    def broadcast_migration_update(migration_id: int, data: dict[str, Any]) -> None:
        room = f"migration_{migration_id}"
        event_data = {
            "event_type": "migration_update",
            "migration_id": migration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        socketio.emit("migration_update", event_data, room=room)
        _get_logger().info(f"Broadcasted migration update to room: {room}")

    @staticmethod
    def broadcast_worker_status(migration_id: int, status: str, worker_type: str = "local") -> None:
        room = f"migration_{migration_id}"
        event_data = {
            "event_type": "worker_status",
            "migration_id": migration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "status": status,
                "worker_type": worker_type,
            },
        }
        socketio.emit("worker_status", event_data, room=room)
        _get_logger().info(f"Broadcasted worker status to room: {room}")

    @staticmethod
    def broadcast_cdc_update(migration_id: int, data: dict[str, Any]) -> None:
        room = f"migration_{migration_id}"
        event_data = {
            "event_type": "cdc_update",
            "migration_id": migration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        socketio.emit("cdc_update", event_data, room=room)
        _get_logger().info(f"Broadcasted CDC update to room: {room}")

    @staticmethod
    def broadcast_replication_lag(migration_id: int, lag_seconds: int, lsn: str) -> None:
        room = f"migration_{migration_id}"
        event_data = {
            "event_type": "replication_lag",
            "migration_id": migration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "lag_seconds": lag_seconds,
                "lsn": lsn,
            },
        }
        socketio.emit("replication_lag", event_data, room=room)
        _get_logger().info(f"Broadcasted replication lag to room: {room}")

    @staticmethod
    def broadcast_schema_drift(migration_id: int, drift_event: dict[str, Any]) -> None:
        room = f"migration_{migration_id}"
        event_data = {
            "event_type": "schema_drift",
            "migration_id": migration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": drift_event,
        }
        socketio.emit("schema_drift", event_data, room=room)
        _get_logger().info(f"Broadcasted schema drift to room: {room}")

    @staticmethod
    def broadcast_approval_request(migration_id: int, approval_data: dict[str, Any]) -> None:
        room = f"migration_{migration_id}"
        event_data = {
            "event_type": "approval_request",
            "migration_id": migration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": approval_data,
        }
        socketio.emit("approval_request", event_data, room=room)
        _get_logger().info(f"Broadcasted approval request to room: {room}")

    @staticmethod
    def broadcast_error(migration_id: int, error_data: dict[str, Any]) -> None:
        room = f"migration_{migration_id}"
        event_data = {
            "event_type": "error",
            "migration_id": migration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": error_data,
        }
        socketio.emit("error", event_data, room=room)
        _get_logger().info(f"Broadcasted error to room: {room}")

    @staticmethod
    def broadcast_heartbeat(migration_id: int, worker_id: str) -> None:
        room = f"migration_{migration_id}"
        event_data = {
            "event_type": "heartbeat",
            "migration_id": migration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "worker_id": worker_id,
            },
        }
        socketio.emit("heartbeat", event_data, room=room)
        _get_logger().info(f"Broadcasted heartbeat to room: {room}")

    @staticmethod
    def broadcast_global_event(event_type: str, data: dict[str, Any]) -> None:
        event_data = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        socketio.emit(event_type, event_data, broadcast=True)
        _get_logger().info(f"Broadcasted global event: {event_type}")

    @staticmethod
    def broadcast_ecs_task_update(task_id: int, data: dict[str, Any]) -> None:
        room = f"ecs_task_{task_id}"
        event_data = {
            "event_type": "ecs_task_update",
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        socketio.emit("ecs_task_update", event_data, room=room)
        _get_logger().info(f"Broadcasted ECS task update to room: {room}")

    @staticmethod
    def join_ecs_task_room(task_id: int) -> None:
        room = f"ecs_task_{task_id}"
        join_room(room)
        _get_logger().info(f"Client joined ECS task room: {room}")

    @staticmethod
    def leave_ecs_task_room(task_id: int) -> None:
        room = f"ecs_task_{task_id}"
        leave_room(room)
        _get_logger().info(f"Client left ECS task room: {room}")


websocket_service = WebSocketService()
