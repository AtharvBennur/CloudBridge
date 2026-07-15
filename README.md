# CloudBridge

**Enterprise Database Migration Platform**

CloudBridge is a production-ready platform for orchestrating, monitoring, and managing database migrations across AWS environments. It provides a comprehensive solution for schema migration, change data capture (CDC), schema drift detection, approval workflows, and rollback management with a premium enterprise SaaS interface.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React/TS)                   │
│  Dashboard · Migrations · CDC · Schema Drift · Approvals   │
│  ECS Tasks · Observability · Notifications · Rollback      │
│  Account · Settings · Help                                  │
├─────────────────────────────────────────────────────────────┤
│                     API Gateway (Nginx)                      │
├─────────────────────────────────────────────────────────────┤
│                    Backend (Flask/Python)                     │
│  Auth · Migrations · CDC · Schema · ECS · Observability    │
│  Notifications · Rollback · Preflight · WebSocket           │
├─────────────────────────────────────────────────────────────┤
│                   Worker Layer (Threads/ECS)                 │
│  Migration Workers · CDC Workers · Schema Workers           │
├─────────────────────────────────────────────────────────────┤
│                     AWS Integration Layer                     │
│  STS AssumeRole · Secrets Manager · CloudFormation          │
│  ECS Fargate · CloudWatch · Cognito                        │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

- **Migration Lifecycle Management** — Create, start, pause, resume, cancel, and retry database migrations with checkpoint-based recovery
- **Change Data Capture (CDC)** — Real-time replication monitoring with WAL-based change tracking
- **Schema Drift Detection** — Automated schema comparison with approval workflows and rollback support
- **AWS Account Integration** — STS AssumeRole across customer accounts with IAM validation
- **ECS/Fargate Orchestration** — Managed container execution for migration workers
- **Pre-flight Validation** — Automated connectivity, permissions, and configuration checks
- **Approval Workflows** — Multi-level schema change approval with risk-based auto-approval
- **Rollback & Recovery** — Checkpoint-based rollback with full migration restart capability
- **Observability** — CloudWatch metrics, audit logging, system health monitoring
- **Notification Center** — Multi-channel delivery (Email, Slack, Webhook) with filtering
- **WebSocket Real-time Updates** — Live migration progress, worker status, and event notifications
- **JWT Authentication** — Token-based auth with Google OAuth integration
- **Theme Support** — Light, dark, and system-preference themes

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite 6, Tailwind CSS, TanStack Query |
| Backend | Python 3.12, Flask 3.1, SQLAlchemy 2.0, Flask-SocketIO |
| Database | PostgreSQL (production), SQLite (development) |
| AWS | STS, Secrets Manager, CloudFormation, ECS/Fargate, CloudWatch |
| Auth | JWT (PyJWT), Google OAuth, AWS Cognito |
| Workers | Threading (local), ECS/Fargate (production) |
| Real-time | WebSocket (Socket.IO) |
| Deployment | Docker, Docker Compose, Nginx |

## Folder Structure

```
cloudbridge/
├── backend/
│   ├── app/
│   │   ├── exceptions/       # Domain-specific exceptions
│   │   ├── middleware/        # Auth, request tracking middleware
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── routes/           # Flask blueprints (15 modules)
│   │   ├── schemas/          # Request/response validation
│   │   ├── services/         # Business logic layer
│   │   ├── utils/            # AWS client utilities
│   │   ├── workers/          # Background migration workers
│   │   ├── config.py         # Environment-based configuration
│   │   ├── errors.py         # Global error handlers
│   │   ├── extensions.py     # Flask extension instances
│   │   └── logging.py        # Structured logging setup
│   ├── migrations/           # Alembic database migrations
│   ├── tests/                # 19 passing test cases
│   ├── Dockerfile            # Multi-stage production build
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/       # UI components (shadcn/ui-style)
│   │   ├── context/          # Auth, Theme React contexts
│   │   ├── lib/              # Utilities, env config
│   │   ├── pages/            # 20 page components
│   │   └── services/         # API client, all service modules
│   ├── Dockerfile            # Multi-stage production build
│   └── nginx.conf            # Production nginx config
├── docs/                     # Complete specification documents
├── docker-compose.yml        # Production-ready orchestration
├── .env.example              # Configuration template
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 22+
- Docker & Docker Compose (optional)

### 1. Clone & Setup

```bash
git clone https://github.com/your-org/cloudbridge.git
cd cloudbridge
```

### 2. Backend Setup

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your configuration
cd backend
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

### 3. Frontend Setup

```bash
cp frontend/.env.example frontend/.env
# Edit frontend/.env with your configuration
cd frontend
npm install
npm run dev
```

### 4. Docker Deployment

```bash
cp .env.example .env
# Edit .env with your configuration
docker compose up --build
```

## AWS Setup

### IAM Permissions

CloudBridge requires specific IAM permissions in your AWS account:

1. **Control Plane Account** (where CloudBridge runs):
   - STS: `AssumeRole` to customer accounts
   - CloudFormation: Create stacks for IAM roles
   - ECS: Run Fargate tasks for migration workers
   - CloudWatch: Create metrics and log groups
   - Secrets Manager: Create secrets for database credentials

2. **Customer Account** (where databases reside):
   - Create an IAM role with the CloudFormation template
   - Establish trust with the CloudBridge control plane account
   - Grant the role read access to source databases and write access to targets

### Environment Variables

Key environment variables (see `backend/.env.example` for complete list):

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Secret key for JWT signing |
| `DATABASE_URL` | Yes | Backend database connection string |
| `AWS_ACCESS_KEY_ID` | Yes | AWS access key for control plane |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS secret key for control plane |
| `CLOUDBRIDGE_AWS_ACCOUNT_ID` | Yes | AWS account ID for trust policy |
| `CORS_ORIGINS` | Yes | Allowed frontend origins |
| `GOOGLE_OAUTH_CLIENT_ID` | No | Google OAuth client ID |
| `SMTP_HOST` | No | SMTP server for email notifications |
| `SLACK_WEBHOOK_URL` | No | Slack webhook for notifications |

## API Overview

| Module | Prefix | Description |
|--------|--------|-------------|
| Auth | `/auth` | Login, logout, session validation, Google OAuth |
| Health | `/health` | Health check with database connectivity |
| Migrations | `/migrations` | Migration job CRUD and lifecycle |
| Migration Engine | `/migration-engine` | Start, pause, resume, cancel, retry |
| AWS Connections | `/aws-connections` | Account registration, STS AssumeRole |
| Database Configs | `/database-configs` | Source/destination database onboarding |
| Pre-flight | `/preflight` | Multi-step migration readiness validation |
| CDC | `/cdc` | Change Data Capture configuration and events |
| Schema Drift | `/schema-drift` | Schema snapshots and drift detection |
| Schema Approval | `/schema-approval` | Approval workflow for schema changes |
| ECS | `/ecs` | Fargate task lifecycle management |
| Observability | `/observability` | Audit logs, metrics, system health |
| Notifications | `/notifications` | Config management and delivery history |
| Rollback | `/rollback` | Checkpoint-based rollback and recovery |
| WebSocket | Socket.IO | Real-time migration and worker updates |

## Testing

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Frontend build verification
cd frontend
npm run build
```

## Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Generate a strong `SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Configure PostgreSQL database
- [ ] Set up AWS credentials with appropriate IAM permissions
- [ ] Configure CORS origins for your frontend domain
- [ ] Enable HTTPS with TLS certificate
- [ ] Set up monitoring and alerting
- [ ] Configure database backup strategy
- [ ] Review and set resource limits in docker-compose.yml

## Developer Guide

### Code Style

- Backend: Follow PEP 8, use type hints, avoid wildcard imports
- Frontend: ESLint + TypeScript strict mode
- Services: Keep route handlers thin, delegate to service layer
- Models: SQLAlchemy declarative with explicit column definitions

### Adding a New Feature

1. Define model in `backend/app/models/`
2. Create schema in `backend/app/schemas/`
3. Implement service in `backend/app/services/`
4. Create routes in `backend/app/routes/`
5. Add frontend service in `frontend/src/services/`
6. Create page component in `frontend/src/pages/`
7. Add route in `frontend/src/App.tsx`
8. Add sidebar link in `frontend/src/components/layout/Sidebar.tsx`
9. Register blueprint in `backend/app/__init__.py`

## License

Proprietary - All rights reserved.

---

Built with CloudBridge — Enterprise Database Migration Platform
