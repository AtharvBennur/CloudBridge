from flask import Flask

from app.config import get_config
from app.errors import register_error_handlers
from app.extensions import cors, db
from app.logging import configure_logging
from app.models.migration import MigrationJob
from app.routes.auth import auth_bp
from app.routes.health import health_bp
from app.routes.migration import migration_bp


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    configure_logging(app)
    register_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)

    with app.app_context():
        db.create_all()

    app.logger.info("CloudBridge backend started with %s config", app.config["ENV_NAME"])
    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(migration_bp)
