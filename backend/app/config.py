import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# override=True ensures the project's .env always takes precedence over stray or
# empty AWS_* variables that may already exist in the OS environment (common on
# Windows machines with the AWS CLI installed). Without this, an empty
# AWS_ACCESS_KEY_ID in the shell would shadow the real credentials in .env and the
# app would incorrectly report "AWS credentials are not configured".
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True)
class BaseConfig:
    ENV_NAME = "base"
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cloudbridge.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = _get_int("PORT", 5000)
    DEBUG = False
    TESTING = False
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174",
        ).split(",")
        if origin.strip()
    ]
    # Ensure CORS_ORIGINS is always a list
    if isinstance(CORS_ORIGINS, str):
        CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # API Configuration
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")
    API_HOST = os.getenv("API_HOST", "localhost")
    API_PORT = _get_int("API_PORT", 5000)
    API_PROTOCOL = os.getenv("API_PROTOCOL", "http")

    # AWS Configuration
    COGNITO_REGION = os.getenv("COGNITO_REGION", "")
    COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
    COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "")
    COGNITO_IDENTITY_POOL_ID = os.getenv("COGNITO_IDENTITY_POOL_ID", "")

    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    CLOUDBRIDGE_AWS_ACCOUNT_ID = os.getenv("CLOUDBRIDGE_AWS_ACCOUNT_ID", "")

    # Lambda migration configuration. These are CloudFormation outputs for Lambda functions.
    CLOUDBRIDGE_ORCHESTRATOR_LAMBDA_ARN = os.getenv("CLOUDBRIDGE_ORCHESTRATOR_LAMBDA_ARN", "")
    CLOUDBRIDGE_WORKER_LAMBDA_ARN = os.getenv("CLOUDBRIDGE_WORKER_LAMBDA_ARN", "")
    CLOUDBRIDGE_VALIDATION_LAMBDA_ARN = os.getenv("CLOUDBRIDGE_VALIDATION_LAMBDA_ARN", "")
    CLOUDBRIDGE_DYNAMODB_TABLE = os.getenv("CLOUDBRIDGE_DYNAMODB_TABLE", "")

    # Shared secret used to authenticate Lambda progress callbacks.
    WORKER_API_SECRET = os.getenv("WORKER_API_SECRET", os.getenv("SECRET_KEY", ""))

    # SMTP Configuration
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = _get_int("SMTP_PORT", 587)
    SMTP_USE_TLS = _get_bool("SMTP_USE_TLS", True)
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_ADDRESS = os.getenv("SMTP_FROM_ADDRESS", "noreply@cloudbridge.io")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "CloudBridge")

    # Slack Configuration
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
    SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#cloudbridge-alerts")
    SLACK_USERNAME = os.getenv("SLACK_USERNAME", "CloudBridge")

    # Webhook Configuration
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

    # WebSocket Configuration
    WEBSOCKET_MESSAGE_QUEUE_URL = os.getenv("WEBSOCKET_MESSAGE_QUEUE_URL", "")
    WEBSOCKET_CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "WEBSOCKET_CORS_ORIGINS",
            "http://localhost:5173,http://localhost:5174",
        ).split(",")
        if origin.strip()
    ]

    # Migration Configuration
    MIGRATION_BATCH_SIZE = _get_int("MIGRATION_BATCH_SIZE", 10000)
    MIGRATION_PARALLEL_WORKERS = _get_int("MIGRATION_PARALLEL_WORKERS", 4)
    MIGRATION_CHECKPOINT_INTERVAL = _get_int("MIGRATION_CHECKPOINT_INTERVAL", 60)
    MIGRATION_MAX_RETRIES = _get_int("MIGRATION_MAX_RETRIES", 3)
    MIGRATION_TIMEOUT = _get_int("MIGRATION_TIMEOUT", 3600)

    # CDC Configuration
    CDC_SLOT_PREFIX = os.getenv("CDC_SLOT_PREFIX", "cloudbridge_cdc_")
    CDC_WAL_RETENTION_HOURS = _get_int("CDC_WAL_RETENTION_HOURS", 24)
    CDC_LAG_THRESHOLD_SECONDS = _get_int("CDC_LAG_THRESHOLD_SECONDS", 30)

    # Schema Drift Configuration
    SCHEMA_DRIFT_CHECK_INTERVAL = _get_int("SCHEMA_DRIFT_CHECK_INTERVAL", 300)
    SCHEMA_DRIFT_AUTO_APPROVE_SAFE = _get_bool("SCHEMA_DRIFT_AUTO_APPROVE_SAFE", True)

    # Observability Configuration
    CLOUDWATCH_METRICS_ENABLED = _get_bool("CLOUDWATCH_METRICS_ENABLED", True)
    CLOUDWATCH_METRICS_NAMESPACE = os.getenv("CLOUDWATCH_METRICS_NAMESPACE", "CloudBridge")
    AUDIT_LOGGING_ENABLED = _get_bool("AUDIT_LOGGING_ENABLED", True)
    AUDIT_LOG_RETENTION_DAYS = _get_int("AUDIT_LOG_RETENTION_DAYS", 90)

    # Rollback Configuration
    ROLLBACK_AUTO_CHECKPOINT = _get_bool("ROLLBACK_AUTO_CHECKPOINT", True)
    CHECKPOINT_RETENTION_DAYS = _get_int("CHECKPOINT_RETENTION_DAYS", 30)


class DevelopmentConfig(BaseConfig):
    ENV_NAME = "development"
    DEBUG = _get_bool("FLASK_DEBUG", True)


class TestingConfig(BaseConfig):
    ENV_NAME = "testing"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


class ProductionConfig(BaseConfig):
    ENV_NAME = "production"


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name: str | None = None) -> type[BaseConfig]:
    selected = config_name or os.getenv("FLASK_ENV", "development")
    return CONFIG_BY_NAME.get(selected, DevelopmentConfig)
