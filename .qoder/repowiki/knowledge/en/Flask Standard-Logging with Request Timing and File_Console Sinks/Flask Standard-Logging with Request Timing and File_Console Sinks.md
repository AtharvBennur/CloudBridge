---
kind: logging_system
name: Flask Standard-Logging with Request Timing and File/Console Sinks
category: logging_system
scope:
    - '**'
source_files:
    - backend/app/logging.py
    - backend/app/__init__.py
    - backend/app/config.py
    - backend/app/errors.py
---

The backend uses Python's built-in `logging` module configured via `logging.config.dictConfig`. There is no third-party logging framework (no structlog, loguru, or gunicorn access-log integration). Logging is set up once during app bootstrap and then accessed through Flask's `app.logger` / `current_app.logger` everywhere.

**Initialization and sinks**
- `backend/app/logging.py::configure_logging(app)` is called from `create_app()` before extensions/blueprints are registered.
- A single `default` formatter emits `%(asctime)s %(levelname)s [%(name)s] %(message)s` — plain text, not JSON.
- Handlers:
  - Always: `StreamHandler` to stdout/stderr (`console`).
  - Optional: `FileHandler` when the `LOG_FILE` environment variable is set; parent directory is auto-created.
- Root logger level is taken from `app.config["LOG_LEVEL"]`, which defaults to `INFO` and is sourced from the `LOG_LEVEL` env var in `BaseConfig`.
- `app.logger.setLevel(...)` is also set explicitly so Flask's own logger matches.

**Request lifecycle logging**
- `before_request` hook records `g._request_start = time.monotonic()`.
- `after_request` hook computes elapsed milliseconds and writes one line per request via `app.logger.info("%s %s %s %.1fms", method, path, status_code, duration_ms)`.
- HTTP error handler (`app/errors.py`) logs client/server errors at `WARNING`/`ERROR` level with method/path/status.

**Usage pattern across modules**
- Services accept an optional `logger` constructor argument and fall back to `current_app.logger` inside methods, enabling test injection while keeping production code simple.
- Routes themselves rarely log directly; they delegate to services. The few route-level calls use `app.logger` (e.g., startup message in `__init__.py`).
- No per-module `getLogger(__name__)` usage was found; all loggers resolve through Flask's root logger.

**Structured fields and correlation**
- No structured/log-correlation fields (no request-id, user-id, tenant-id) are attached to log records. The only contextual data comes from positional arguments passed into the message string.
- Audit events are persisted to a database model (`AuditLog`) rather than emitted as log records.

**Environment knobs**
| Variable | Default | Effect |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Root logger level (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FILE` | unset | Path to append-only file sink; omit for console-only |

**What is NOT present**
- No JSON formatter, no external sink (CloudWatch Logs, ELK, Datadog agent).
- No log rotation configuration.
- No Gunicorn/Uvicorn access-log setup; request lines come solely from the Flask middleware.
- Frontend (React SPA) has no dedicated logging layer — it relies on browser devtools.