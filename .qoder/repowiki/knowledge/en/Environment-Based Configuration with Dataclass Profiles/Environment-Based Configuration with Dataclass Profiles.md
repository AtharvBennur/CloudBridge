---
kind: configuration_system
name: Environment-Based Configuration with Dataclass Profiles
category: configuration_system
scope:
    - '**'
source_files:
    - backend/app/config.py
    - backend/app/__init__.py
    - backend/run.py
    - backend/.env.example
    - frontend/src/lib/env.ts
    - frontend/.env.example
    - .env.example
---

CloudBridge uses a simple, environment-variable-driven configuration system built around Python dataclasses and the python-dotenv loader. There is no YAML/JSON/TOML config file format — every setting is an environment variable with a documented default.

**Backend (Flask)**
- `backend/app/config.py` defines a frozen `BaseConfig` dataclass whose fields are all read from `os.getenv(...)` with sensible defaults. Helper functions `_get_bool` and `_get_int` normalize string env values into typed booleans/integers.
- Three profile subclasses exist: `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`. They only override flags like `DEBUG` / `TESTING`; all other settings remain on `BaseConfig`.
- `CONFIG_BY_NAME` maps the string key to the class, and `get_config(config_name)` selects it based on `FLASK_ENV` (defaulting to `development`).
- `app/__init__.py::create_app()` calls `app.config.from_object(get_config(config_name))`, so Flask's `app.config` becomes a direct view onto the selected dataclass. Extensions (`db`, `cors`, `socketio`) read their settings straight from `app.config[...]`.
- `run.py` enforces that `SECRET_KEY` must be set when not in debug mode, providing a runtime safety check.
- `backend/.env.example` documents every supported env var with comments indicating required vs optional and production guidance.

**Frontend (React + Vite)**
- `frontend/src/lib/env.ts` exposes a single `env` object reading `import.meta.env.VITE_*` variables. It derives WebSocket URLs from the API base URL and groups feature flags under `env.features.*` and UI toggles under `env.ui.*`.
- `frontend/.env.example` lists all `VITE_` variables; the top-level `.env.example` mirrors them for convenience during Docker Compose development.
- Feature flags are compile-time constants (Vite replaces `import.meta.env` at build time), so toggling features requires rebuilding the SPA.

**Docker Compose**
- The root `.env.example` aggregates both backend and frontend variables plus compose-specific ones (`COMPOSE_PROJECT_NAME`, `BACKEND_PORT`, `FRONTEND_PORT`) so a single file can drive the whole stack.

**Conventions & Rules**
1. Every new setting belongs as a field on `BaseConfig` with a default value; add a matching `VITE_*` constant in the frontend `env.ts` if the UI needs it.
2. Document each env var in `backend/.env.example` (and mirror in the root `.env.example`) with `[REQUIRED]` / `[OPTIONAL]` tags and a one-line description.
3. Use `_get_bool` / `_get_int` helpers for non-string types — never call `os.getenv` directly outside `config.py`.
4. Never hard-code secrets; always source them from env vars or AWS Secrets Manager via the `SECRETS_PREFIX`-based service layer.
5. Keep per-environment overrides minimal (only `DEBUG`, `TESTING`, `SQLALCHEMY_DATABASE_URI`); prefer env var overrides over subclass churn.
6. Frontend feature flags are build-time; plan flag additions carefully since they require a rebuild of the SPA.