"""
Purpose:
This file contains the WebSocket event handlers for real-time communication.

Why:
WebSockets enable live updates to the frontend without page refreshes.

Architecture:
WebSocket Routes
↓
WebSocket Service
↓
Flask-SocketIO
"""

from flask import request
from flask_socketio import disconnect, emit

from app.extensions import socketio
from app.services.websocket_service import websocket_service


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    print(f"Client connected: {request.sid}")
    emit("connected", {"message": "Connected to CloudBridge WebSocket server"})


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    print(f"Client disconnected: {request.sid}")


@socketio.on("join_migration")
def handle_join_migration(data):
    """Handle client joining a migration room."""
    migration_id = data.get("migration_id")
    if migration_id:
        websocket_service.join_migration_room(migration_id)
        emit("joined_migration", {"migration_id": migration_id, "message": f"Joined migration {migration_id} room"})


@socketio.on("leave_migration")
def handle_leave_migration(data):
    """Handle client leaving a migration room."""
    migration_id = data.get("migration_id")
    if migration_id:
        websocket_service.leave_migration_room(migration_id)
        emit("left_migration", {"migration_id": migration_id, "message": f"Left migration {migration_id} room"})


@socketio.on("join_ecs_task")
def handle_join_ecs_task(data):
    """Handle client joining an ECS task room."""
    task_id = data.get("task_id")
    if task_id:
        websocket_service.join_ecs_task_room(task_id)
        emit("joined_ecs_task", {"task_id": task_id, "message": f"Joined ECS task {task_id} room"})


@socketio.on("leave_ecs_task")
def handle_leave_ecs_task(data):
    """Handle client leaving an ECS task room."""
    task_id = data.get("task_id")
    if task_id:
        websocket_service.leave_ecs_task_room(task_id)
        emit("left_ecs_task", {"task_id": task_id, "message": f"Left ECS task {task_id} room"})


@socketio.on("ping")
def handle_ping():
    """Handle ping from client."""
    emit("pong", {"timestamp": "pong"})
