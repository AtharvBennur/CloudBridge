import logging
import os
import traceback
from logging.config import dictConfig
from datetime import datetime

from flask import Flask, request, g
import time as _time


class StructuredFormatter(logging.Formatter):
    """Structured JSON-like formatter for production logging."""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        if hasattr(record, 'migration_id'):
            log_data["migration_id"] = record.migration_id
        if hasattr(record, 'aws_connection_id'):
            log_data["aws_connection_id"] = record.aws_connection_id
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
            
        return str(log_data).replace("'", '"')


def configure_logging(app: Flask) -> None:
    log_level = app.config.get("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "")
    log_format = os.getenv("LOG_FORMAT", "text")  # "text" or "json"

    formatter_class = StructuredFormatter if log_format == "json" else logging.Formatter
    
    if log_format == "text":
        formatter_format = "%(asctime)s %(levelname)s [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
    else:
        formatter_format = None

    handlers: dict[str, dict] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    }
    handler_names = ["console"]

    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "default",
        }
        handler_names.append("file")

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": formatter_format,
                    "class": formatter_class.__name__ if log_format == "json" else "",
                }
            },
            "handlers": handlers,
            "root": {
                "level": log_level,
                "handlers": handler_names,
            },
        }
    )
    app.logger.setLevel(logging.getLevelName(log_level))

    @app.before_request
    def _start_timer():
        g._request_start = _time.monotonic()
        g._request_id = os.urandom(8).hex()

    @app.after_request
    def _log_request(response):
        duration_ms = (_time.monotonic() - g.get("_request_start", _time.monotonic())) * 1000
        request_id = g.get("_request_id", "unknown")
        
        # Structured request logging
        app.logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "user_agent": request.headers.get("User-Agent", ""),
                "remote_addr": request.remote_addr,
            }
        )
        return response

    @app.errorhandler(Exception)
    def _log_exception(error):
        """Log unhandled exceptions with full context."""
        request_id = g.get("_request_id", "unknown")
        
        app.logger.error(
            "Unhandled exception",
            exc_info=True,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        )
        return error
