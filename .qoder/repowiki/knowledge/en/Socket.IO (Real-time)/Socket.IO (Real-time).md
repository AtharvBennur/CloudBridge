---
kind: external_dependency
name: Socket.IO (Real-time)
slug: socketio
category: external_dependency
category_hints:
    - framework_behavior
scope:
    - '**'
---

### Socket.IO (Real-time)
- **Role in this repo**: Bidirectional WebSocket channel for live migration progress, worker status updates, and event notifications between Flask backend and React frontend.
- **Durable usage model**: Events are emitted from workers/services and subscribed to by pages (Dashboard, MigrationDetail, etc.) for real-time UI updates. CORS origins configurable via `WEBSOCKET_CORS_ORIGINS` env var separate from HTTP CORS.