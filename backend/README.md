# CloudBridge Backend

Flask API backend for CloudBridge — a managed database migration platform with real-time monitoring, CDC replication, schema drift detection, and multi-account AWS orchestration.

## Features

- **Migration Engine** — Batch and streaming data migration with parallel workers, checkpointing, and rollback support.
- **CDC Replication** — PostgreSQL logical replication with real-time lag monitoring and WAL management.
- **Schema Drift Detection** — Automated schema comparison, drift alerts, and approval workflows.
- **AWS ECS Workers** — Task orchestration for migration workers via ECS/Fargate with CloudWatch logging.
- **AWS Cognito Auth** — User authentication and JWT token validation.
- **Multi-Account AWS** — Cross-account access via STS AssumeRole.
- **Real-Time WebSocket** — Live progress, worker status, and event broadcasting via Socket.IO.
- **Notifications** — Email (SMTP), Slack, and webhook integrations.
- **Observability** — CloudWatch metrics, audit logging, and structured request logging.
- **Rollback** — Point-in-time rollback via automated checkpoints.
- **Preflight Checks** — Pre-migration validation of source/target connectivity, permissions, and capacity.

## Stack

- Python 3.12
- Flask application factory
- Flask-SQLAlchemy / Alembic
- Flask-SocketIO
- Flask-CORS
- boto3 (AWS SDK)
- Gunicorn

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # fill in your credentials
python run.py
```

The API runs on `http://localhost:5000`.

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in required values.

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Production | Flask secret key for sessions |
| `DATABASE_URL` | Yes | SQLAlchemy database URI |
| `COGNITO_USER_POOL_ID` | Production | Cognito User Pool ID |
| `COGNITO_CLIENT_ID` | Production | Cognito App Client ID |
| `AWS_ACCESS_KEY_ID` | Production | AWS credentials for control plane |
| `AWS_SECRET_ACCESS_KEY` | Production | AWS credentials for control plane |

See `.env.example` for the full list of configuration variables.

## Production Run

```powershell
gunicorn --bind 0.0.0.0:5000 --workers 4 "app:create_app()"
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Health check with database connectivity |
| `POST /auth/login` | Google OAuth login |
| `GET /auth/me` | Current user profile |
| `GET /migrations` | List migration jobs |
| `POST /migrations` | Create migration job |
| `GET /migrations/<id>` | Migration job details |
| `POST /migrations/<id>/start` | Start migration |
| `POST /migrations/<id>/pause` | Pause migration |
| `POST /migrations/<id>/resume` | Resume migration |
| `POST /migrations/<id>/cancel` | Cancel migration |
| `GET /preflight/<id>` | Run preflight checks |
| `GET /cdc/<id>` | CDC configuration |
| `POST /cdc/<id>/start` | Start CDC replication |
| `POST /cdc/<id>/stop` | Stop CDC replication |
| `GET /schema-drift/<id>` | Get schema drift events |
| `POST /schema-approval/<id>` | Approve/reject schema changes |
| `GET /ecs/tasks` | List ECS tasks |
| `POST /ecs/tasks` | Launch ECS task |
| `GET /observability/metrics` | CloudWatch metrics |
| `GET /observability/audit-logs` | Audit log entries |
| `GET /notifications` | Notification configs |
| `POST /rollback/<id>` | Rollback to checkpoint |
| `WS /socket.io` | WebSocket for real-time events |
