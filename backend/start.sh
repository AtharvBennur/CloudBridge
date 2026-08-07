#!/bin/bash
# Start script for Render deployment
# This handles both the web server and WebSocket support

export PORT=${PORT:-5000}
export DATABASE_URL=${DATABASE_URL:-postgresql://user:pass@localhost:5432/cloudbridge}

# Run the Flask app with Socket.IO support
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 300 app:app