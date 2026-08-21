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
from flask_socketio import emit

from app.services.websocket_service import websocket_service


def handle_connect():
    """Handle client connection."""
    print(f"Client connected: {request.sid}")
    emit("connected", {"message": "Connected to CloudBridge WebSocket server"})


def handle_disconnect():
    """Handle client disconnection."""
    print(f"Client disconnected: {request.sid}")


def handle_join_migration(data):
    """Handle client joining a migration room."""
    migration_id = data.get("migration_id")
    if migration_id:
        websocket_service.join_migration_room(migration_id)
        emit("joined_migration", {"migration_id": migration_id, "message": f"Joined migration {migration_id} room"})


def handle_leave_migration(data):
    """Handle client leaving a migration room."""
    migration_id = data.get("migration_id")
    if migration_id:
        websocket_service.leave_migration_room(migration_id)
        emit("left_migration", {"migration_id": migration_id, "message": f"Left migration {migration_id} room"})


def handle_ping():
    """Handle ping from client."""
    emit("pong", {"timestamp": "pong"})
