---
kind: build_system
name: Docker Compose Monorepo Build & Containerization
category: build_system
scope:
    - '**'
source_files:
    - docker-compose.yml
    - backend/Dockerfile
    - frontend/Dockerfile
    - backend/requirements.txt
    - frontend/package.json
    - backend/alembic.ini
    - backend/.env.example
    - frontend/.env.example
    - frontend/nginx.conf
---

CloudBridge uses a Docker Compose-driven monorepo build system that assembles three services — a Flask backend, a React/Vite frontend, and a shared PostgreSQL database — into a single local development stack. There is no Makefile or CI pipeline in the repository; the entire build, test, and run workflow is expressed through Dockerfiles and `docker-compose.yml`.

**Build toolchain per service**
- Backend (`backend/`): Python 3.12 with pip. Dependencies are pinned in `requirements.txt`. The multi-stage Dockerfile installs build tools (build-essential, libpq-dev) in a builder stage, then copies only site-packages into a slim runtime image. The app runs under gunicorn behind a non-root user.
- Frontend (`frontend/`): Node 22 + Vite + TypeScript. `package.json` scripts define `dev`, `build`, `lint`, and `preview`. A two-stage Dockerfile builds assets with `npm ci && npm run build` and serves them from nginx:alpine, proxying `/api/` and `/socket.io/` to the backend.
- Database: `postgres:16-alpine` with a named volume for persistence and a healthcheck via `pg_isready`.

**Orchestration**
`docker-compose.yml` defines the three services on a shared bridge network `cloudbridge`. The backend depends on the db being healthy; the frontend depends on the backend being healthy. Ports are exposed via environment-variable defaults (`DB_PORT`, `BACKEND_PORT`, `FRONTEND_PORT`). The frontend receives `VITE_API_BASE_URL` / `VITE_WS_BASE_URL` as Docker build args so the SPA can be reconfigured at build time without code changes.

**Configuration management**
- Both sides ship `.env.example` files documenting every supported variable (Flask, AWS Cognito/OAuth, ECS, Secrets Manager, SMTP, Slack, WebSocket queue, migration/CDC/rollback tuning, feature flags). Runtime values are loaded via `python-dotenv` on the backend and Vite's `import.meta.env.*` on the frontend.
- Alembic is configured in `backend/alembic.ini` pointing at `migrations/`; the default URL is SQLite (`sqlite:///cloudbridge.db`) for local dev, while production uses the `DATABASE_URL` env var (PostgreSQL).

**Security & hardening in images**
- Both Dockerfiles create a non-root user (`cloudbridge`, uid 1000) and drop privileges before running.
- Nginx sets security headers (`X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`, CSP) and disables server tokens.
- Gzip compression and long-lived immutable caching for `/assets` are enabled.

**Testing hooks**
- Backend tests are driven by pytest (`pytest.ini`, `tests/`); they rely on an in-memory SQLite DB when `FLASK_ENV=testing` unless `TEST_DATABASE_URL` overrides it.
- No automated CI configuration (GitHub Actions, etc.) exists in this snapshot; the build system is purely local/container-based.

**Conventions developers should follow**
- Add new Python dependencies to `backend/requirements.txt` and pin versions; rebuild the backend image after changes.
- Add new frontend dependencies to `frontend/package.json` and use `npm ci` during builds.
- Do not commit `.env` files; copy from `.env.example` and fill secrets locally.
- When changing frontend API endpoints, ensure the nginx reverse-proxy paths (`/api/`, `/socket.io/`) remain aligned.
- For production deployments outside Docker Compose, replicate the same env vars documented in the `.env.example` files.