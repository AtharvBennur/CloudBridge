---
kind: dependency_management
name: Python and Node.js dependency manifests with pinned versions
category: dependency_management
scope:
    - '**'
source_files:
    - backend/requirements.txt
    - backend/Dockerfile
    - frontend/package.json
    - frontend/package-lock.json
---

The repository manages third-party dependencies for its two language stacks using the standard, lightweight approaches for each ecosystem. There is no vendoring, private registry configuration, or monorepo-level lockfile — each subproject declares its own dependencies independently.

**Backend (Python / Flask)**
- Dependencies are declared in `backend/requirements.txt` using exact pinning (`==`) for every package (e.g. `Flask==3.1.0`, `boto3==1.35.81`, `SQLAlchemy==2.0.36`).
- No `pip freeze` output, `Pipfile`, `poetry.lock`, or `pyproject.toml` exists; `requirements.txt` is the single source of truth.
- The backend Dockerfile (`backend/Dockerfile`) installs dependencies via `pip install -r requirements.txt` during the build stage, so container images are reproducible from this file alone.
- No `.venv` directory is committed to version control (it appears only under `backend/.venv` locally); virtual environments are expected to be created per developer machine.

**Frontend (React / Vite)**
- Dependencies are declared in `frontend/package.json` using caret ranges (`^`) for both `dependencies` and `devDependencies`.
- A `frontend/package-lock.json` (lockfileVersion 3) is committed alongside `package.json`, locking transitive resolutions to exact versions and integrity hashes at install time.
- The frontend has no vendored `node_modules`; it relies on npm's default registry resolution plus the lockfile for reproducibility.

**Conventions observed**
- Python pins every runtime and test dependency to an exact version in a flat `requirements.txt`; there is no split between production/dev/test requirement files.
- Frontend uses semver-compatible ranges in `package.json` but achieves deterministic builds through the committed `package-lock.json`.
- Neither stack configures a custom PyPI/npm registry, proxy, or authentication token — all packages resolve against public registries.
- Dependency updates are manual: developers edit `requirements.txt` / `package.json` directly rather than relying on automated tooling such as Dependabot or Renovate.