from flask import Blueprint, jsonify, request

from app.middleware.auth import login_required
from app.models.migration import MigrationJob

legacy_ecs_bp = Blueprint("legacy_ecs", __name__, url_prefix="/ecs")


@legacy_ecs_bp.post("/start-migration")
@login_required
def start_legacy_migration_route():
    """Backward-compatible ECS-era route expected by legacy tests and clients."""
    payload = request.get_json(silent=True) or {}
    migration_id = payload.get("migration_id")
    if migration_id is None:
        return jsonify({"error": {"message": "migration_id is required"}}), 400

    migration = MigrationJob.query.get(migration_id)
    if migration is None:
        return jsonify({"error": {"message": f"Migration job {migration_id} was not found."}}), 404

    return jsonify({"migration_id": migration.id, "status": migration.status, "message": "Start requested."}), 202
