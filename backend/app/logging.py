import logging
import os
from logging.config import dictConfig

from flask import Flask, request, g
import time as _time


def configure_logging(app: Flask) -> None:
    log_level = app.config.get("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "")

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
            "class": "logging.FileHandler",
            "filename": log_file,
            "formatter": "default",
        }
        handler_names.append("file")

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
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

    @app.after_request
    def _log_request(response):
        duration_ms = (_time.monotonic() - g.get("_request_start", _time.monotonic())) * 1000
        app.logger.info(
            "%s %s %s %.1fms",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response
