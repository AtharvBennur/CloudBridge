from flask import Flask

from app.config import get_config
from app.errors import register_error_handlers
from app.extensions import cors, db, socketio
from app.logging import configure_logging
from app.middleware import RequestMiddleware
from app.models.aws_connection import AWSConnection
from app.models.database_config import DatabaseConfig
from app.models.migration import MigrationJob
from app.models.migration_checkpoint import MigrationCheckpoint
from app.models.cdc_config import CDCConfig
from app.models.cdc_event import CDCEvent
from app.models.schema_snapshot import SchemaSnapshot, SchemaDriftEvent
from app.models.ecs_task import ECSTask
from app.models.audit_log import AuditLog
from app.models.notification import NotificationConfig, Notification
from app.routes.auth import auth_bp
from app.routes.aws_connection import aws_connection_bp
from app.routes.database_config import database_config_bp
from app.routes.health import health_bp
from app.routes.migration import migration_bp
from app.routes.migration_engine import migration_engine_bp
from app.routes.preflight import preflight_bp
from app.routes.cdc import cdc_bp
from app.routes.schema_drift import schema_drift_bp
from app.routes.schema_approval import schema_approval_bp
from app.routes.ecs import ecs_bp
from app.routes.observability import observability_bp
from app.routes.notification import notification_bp
from app.routes.rollback import rollback_bp
from app.routes.websocket import handle_connect, handle_disconnect, handle_join_migration, handle_leave_migration, handle_join_ecs_task, handle_leave_ecs_task, handle_ping


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    configure_logging(app)
    register_extensions(app)
    register_middleware(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_websocket_handlers(app)

    with app.app_context():
        db.create_all()

    app.logger.info("CloudBridge backend started with %s config", app.config["ENV_NAME"])
    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})


def register_middleware(app: Flask) -> None:
    RequestMiddleware(app)


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(migration_bp)
    app.register_blueprint(migration_engine_bp)
    app.register_blueprint(aws_connection_bp)
    app.register_blueprint(database_config_bp)
    app.register_blueprint(preflight_bp)
    app.register_blueprint(cdc_bp)
    app.register_blueprint(schema_drift_bp)
    app.register_blueprint(schema_approval_bp)
    app.register_blueprint(ecs_bp)
    app.register_blueprint(observability_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(rollback_bp)


def register_websocket_handlers(app: Flask) -> None:
    """Register WebSocket event handlers."""
    cors_origins = app.config.get("CORS_ORIGINS", "*")
    socketio.init_app(app, cors_allowed_origins=cors_origins, async_mode="threading")

    socketio.on("connect")(handle_connect)
    socketio.on("disconnect")(handle_disconnect)
    socketio.on("join_migration")(handle_join_migration)
    socketio.on("leave_migration")(handle_leave_migration)
    socketio.on("join_ecs_task")(handle_join_ecs_task)
    socketio.on("leave_ecs_task")(handle_leave_ecs_task)
    socketio.on("ping")(handle_ping)
