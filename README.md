# CloudBridge

Enterprise-grade database migration platform with CDC, schema drift detection, approval workflows, and rollback capabilities.

## Overview

CloudBridge is a production-ready full-stack platform for managing database migrations at scale. It provides:

- **Change Data Capture (CDC)**: Real-time replication with PostgreSQL WAL streaming
- **Schema Drift Detection**: Continuous monitoring and automatic drift detection
- **Approval Workflow**: Pause on dangerous changes with manual approval
- **ECS/Fargate Execution**: Scalable migration workers on AWS
- **Observability**: CloudWatch metrics, audit logs, and system monitoring
- **Notifications**: Email, Slack, and webhook integrations
- **Rollback**: Checkpoint-based recovery with resume support
- **Real-time Updates**: WebSocket-powered live dashboard

## Architecture

### Backend
- **Framework**: Flask 3 with application factory pattern
- **Database**: SQLAlchemy ORM with Alembic migrations
- **Authentication**: Google OAuth (configurable)
- **AWS Integration**: STS AssumeRole, Secrets Manager, ECS/Fargate, CloudWatch
- **Real-time**: Flask-SocketIO for WebSocket communication
- **Logging**: Structured logging with configurable levels

### Frontend
- **Framework**: React 19 + Vite + TypeScript
- **Styling**: Tailwind CSS with shadcn/ui components
- **State**: TanStack Query for data fetching
- **Routing**: React Router with protected routes
- **Animations**: Framer Motion for smooth transitions
- **Real-time**: Socket.IO client for live updates

## Prerequisites

### System Requirements
- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **npm**: 9 or higher

### AWS Prerequisites
- AWS Account with appropriate IAM permissions
- IAM user with programmatic access (for control plane)
- ECS Cluster and Task Definition (for migration workers)
- CloudWatch Log Group (for worker logs)

### Required IAM Permissions

The CloudBridge control plane IAM user requires:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole",
        "secretsmanager:CreateSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:DeleteSecret",
        "secretsmanager:ListSecrets",
        "ecs:RunTask",
        "ecs:StopTask",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "cloudwatch:PutMetricData",
        "cloudwatch:GetMetricStatistics"
      ],
      "Resource": "*"
    }
  ]
}
```

Customer accounts require an IAM role with trust policy allowing CloudBridge to assume it.

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/AtharvBennur/CloudBridge.git
cd CloudBridge
```

### 2. Configure Environment

**Backend:**

```bash
cd backend
copy .env.example .env
```

Edit `.env` and fill in your credentials:
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `GOOGLE_OAUTH_CLIENT_ID`: Google OAuth Client ID from Google Cloud Console
- `GOOGLE_OAUTH_CLIENT_SECRET`: Google OAuth Client Secret from Google Cloud Console
- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `CLOUDBRIDGE_AWS_ACCOUNT_ID`: Your AWS account ID
- `ECS_CLUSTER_NAME`: Your ECS cluster name
- `ECS_TASK_DEFINITION`: Your ECS task definition
- SMTP/Slack/Webhook credentials for notifications

**Frontend:**

```bash
cd frontend
copy .env.example .env
```

Edit `.env` and configure:
- `VITE_API_BASE_URL`: Backend API URL (default: `http://localhost:5000`)
- `VITE_GOOGLE_OAUTH_CLIENT_ID`: Google OAuth Client ID from Google Cloud Console

### 3. Backend Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python -m flask db upgrade  # Run database migrations
python run.py
```

Backend will start on `http://localhost:5000`

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will start on `http://localhost:5173`

### 5. Verify Installation

```bash
# Backend health check
Invoke-RestMethod http://localhost:5000/health

# Should return: {"status": "healthy"}
```

Open `http://localhost:5173` in your browser to access the CloudBridge dashboard.

## Project Structure

```
CloudBridge/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask application factory
│   │   ├── config.py            # Configuration management
│   │   ├── extensions.py        # Flask extensions (DB, CORS, SocketIO)
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas for API
│   │   ├── routes/              # API blueprints
│   │   ├── services/            # Business logic layer
│   │   ├── workers/             # Background workers
│   │   ├── utils/               # Utility functions
│   │   └── middleware/          # Custom middleware
│   ├── migrations/              # Alembic migration files
│   ├── tests/                   # Backend tests
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example             # Environment template
│   └── run.py                   # Application entry point
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── layout/          # Layout components (Sidebar, Navbar)
│   │   │   ├── routing/         # Routing components
│   │   │   └── ui/              # UI components (shadcn/ui)
│   │   ├── pages/               # Page components
│   │   ├── services/            # API service layer
│   │   ├── lib/                 # Utility libraries
│   │   └── App.tsx              # Main application component
│   ├── public/                  # Static assets
│   ├── package.json             # Node dependencies
│   ├── .env.example             # Environment template
│   └── vite.config.ts           # Vite configuration
├── docker-compose.yml           # Docker orchestration
└── README.md                    # This file
```

## Database Migrations

### Create New Migration

```bash
cd backend
python -m flask db migrate -m "description of changes"
```

### Apply Migrations

```bash
python -m flask db upgrade
```

### Rollback Migration

```bash
python -m flask db downgrade
```

## Running Tests

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Deployment

### Backend Deployment

**Production Configuration:**

1. Set `FLASK_ENV=production` in `.env`
2. Use PostgreSQL instead of SQLite:
   ```
   DATABASE_URL=postgresql://user:password@host:port/database
   ```
3. Set a strong `SECRET_KEY`
4. Disable debug mode: `FLASK_DEBUG=false`
5. Use production WSGI server (Gunicorn):
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
   ```

**Docker Deployment:**

```bash
docker build -t cloudbridge-backend ./backend
docker run -p 5000:5000 --env-file .env cloudbridge-backend
```

### Frontend Deployment

**Production Build:**

```bash
cd frontend
npm run build
```

The build output will be in `frontend/dist/`. Serve with any static file server (Nginx, Apache, etc.).

**Docker Deployment:**

```bash
docker build -t cloudbridge-frontend ./frontend
docker run -p 5173:80 cloudbridge-frontend
```

### Docker Compose

```bash
docker-compose up -d
```

## Feature Configuration

### Enable/Disable Features

Features can be controlled via environment variables in `frontend/.env`:

```bash
VITE_FEATURE_CDC=true
VITE_FEATURE_SCHEMA_DRIFT=true
VITE_FEATURE_APPROVALS=true
VITE_FEATURE_ECS=true
VITE_FEATURE_OBSERVABILITY=true
VITE_FEATURE_NOTIFICATIONS=true
VITE_FEATURE_ROLLBACK=true
```

### WebSocket Configuration

WebSocket URL is auto-derived from `VITE_API_BASE_URL`. Override with:

```bash
VITE_WS_BASE_URL=ws://your-backend-url
```

## Authentication

### Google OAuth Setup

CloudBridge uses Google OAuth for authentication. To set it up:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:5173` (or your production URL)
5. Copy Client ID and Client Secret
6. Add to backend `.env`:
   - `GOOGLE_OAUTH_CLIENT_ID=your-client-id`
   - `GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret`
7. Add to frontend `.env`:
   - `VITE_GOOGLE_OAUTH_CLIENT_ID=your-client-id`

### Local Authentication

For development without Google OAuth, you can use the local authentication:
- Email: any valid email address
- Password: minimum 8 characters

## Troubleshooting

### Backend Issues

**ModuleNotFoundError: No module named 'flask_socketio'**
```bash
pip install flask-socketio
```

**Database connection errors**
- Verify `DATABASE_URL` in `.env`
- Ensure database server is running
- Check credentials

**AWS authentication errors**
- Verify AWS credentials in `.env`
- Check IAM permissions
- Ensure `CLOUDBRIDGE_AWS_ACCOUNT_ID` is correct

**Google OAuth errors**
- Verify Google OAuth credentials in `.env`
- Check redirect URIs match in Google Cloud Console
- Ensure OAuth consent screen is configured

### Frontend Issues

**Module not found errors**
```bash
npm install
```

**API connection errors**
- Verify `VITE_API_BASE_URL` in `.env`
- Ensure backend is running
- Check CORS configuration

**WebSocket connection errors**
- Verify WebSocket URL
- Check backend WebSocket configuration
- Ensure no firewall blocking WebSocket connections

**Dark/Light mode not working**
- Check browser console for errors
- Verify ThemeContext is properly initialized
- Check localStorage for theme settings

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review configuration examples

## License

Proprietary - All rights reserved
