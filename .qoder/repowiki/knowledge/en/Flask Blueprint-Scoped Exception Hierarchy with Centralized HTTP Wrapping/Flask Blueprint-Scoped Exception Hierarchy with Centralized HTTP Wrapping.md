---
kind: error_handling
name: Flask Blueprint-Scoped Exception Hierarchy with Centralized HTTP Wrapping
category: error_handling
scope:
    - '**'
source_files:
    - backend/app/errors.py
    - backend/app/__init__.py
    - backend/app/exceptions/auth.py
    - backend/app/exceptions/migration.py
    - backend/app/exceptions/aws_connection.py
    - backend/app/exceptions/cdc.py
    - backend/app/exceptions/ecs.py
    - backend/app/exceptions/notification.py
    - backend/app/exceptions/schema_approval.py
    - backend/app/exceptions/schema_drift.py
    - backend/app/exceptions/rollback.py
    - backend/app/exceptions/observability.py
    - backend/app/routes/auth.py
    - backend/app/routes/migration.py
---

CloudBridge uses a layered error-handling strategy built on Flask's exception system. Domain-specific exceptions are defined per feature area under `backend/app/exceptions/<feature>.py`, each following a consistent base-class pattern (e.g. `MigrationError`, `AuthError`, `AWSConnectionError`) with subclasses for validation, not-found, and integration failures. Routes import these types and register blueprint-scoped `@bp.errorhandler` handlers that return a uniform JSON shape `{"error": {"message": ...}}` mapped to appropriate HTTP codes (400 for validation/service errors, 404 for not-found). A central `app.errors.register_error_handlers(app)` call — invoked from `create_app()` in `app/__init__.py` — installs two global Flask errorhandlers: one for `werkzeug.exceptions.HTTPException` (returns `{"error": {"code", "message", "status"}}` using the HTTP status name) and one catch-all for `Exception` that logs the full traceback and returns a generic 500 response. Validation inside Pydantic-style schema classes raises plain `ValueError`s; these bubble up through routes and are caught by the global `HTTPException` handler only if converted, otherwise they fall through to the unhandled-exception handler. No custom middleware transforms errors beyond the existing `RequestMiddleware`; there is no centralized service-layer error mapper, so services raise domain exceptions directly and routes translate them.