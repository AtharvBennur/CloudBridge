---
kind: external_dependency
name: PostgreSQL
slug: postgresql
category: external_dependency
category_hints:
    - migration_status
scope:
    - '**'
---

### PostgreSQL
- **Role in this repo**: Production relational database for CloudBridge metadata (users, migrations, CDC configs, audit logs).
- **Migration status**: Development uses SQLite (`sqlite:///cloudbridge.db`) per default `DATABASE_URL`; production switches to PostgreSQL 16 via docker-compose service named `db`. Connection string passed as `postgresql://cloudbridge:cloudbridge_dev@db:5432/cloudbridge`.
- **Integration point**: SQLAlchemy ORM with `psycopg2-binary` driver; Alembic handles schema migrations under `backend/migrations/`.
- **Client constraint**: Requires health check (`pg_isready`) before backend starts; persistent volume `pgdata` for data durability across container restarts.