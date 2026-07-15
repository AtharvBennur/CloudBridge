import time

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    db_ok = True
    try:
        db.session.execute(text("SELECT 1"))
        db.session.commit()
    except Exception:
        db_ok = False

    status = "healthy" if db_ok else "degraded"
    payload = {
        "status": status,
        "database": "connected" if db_ok else "disconnected",
        "timestamp": time.time(),
    }
    return jsonify(payload), 200 if db_ok else 503
