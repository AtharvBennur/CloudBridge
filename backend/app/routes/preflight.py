from flask import Blueprint, jsonify, request

from app.models.aws_connection import AWSConnection
from app.models.database_config import DatabaseConfig
from app.services.preflight_service import PreflightService

preflight_bp = Blueprint("preflight", __name__, url_prefix="/preflight")
preflight_service = PreflightService()


@preflight_bp.post("")
def run_preflight():
    payload = request.get_json(silent=True) or {}
    aws_connection_id = payload.get("aws_connection_id")
    database_config_id = payload.get("database_config_id")
    source_db_id = payload.get("source_db_id")
    destination_db_id = payload.get("destination_db_id")

    connection = AWSConnection.query.get(aws_connection_id) if aws_connection_id is not None else None
    if connection is None:
        return jsonify({"error": {"message": "AWS connection was not found."}}), 404

    # Resolve database IDs with backward compatibility
    if database_config_id is not None:
        db_cfg = DatabaseConfig.query.get(database_config_id)
        if db_cfg:
            if db_cfg.purpose == "SOURCE":
                source_db_id = db_cfg.id
            else:
                destination_db_id = db_cfg.id

    try:
        report = preflight_service.execute(
            aws_connection_id=connection.id,
            source_db_id=source_db_id,
            destination_db_id=destination_db_id,
        )
        return jsonify(report), 200
    except ValueError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
    except Exception as exc:
        return jsonify({"error": {"message": f"Pre-flight error: {exc}"}}), 500
