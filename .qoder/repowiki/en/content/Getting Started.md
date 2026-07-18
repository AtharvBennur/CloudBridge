# Getting Started

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [docker-compose.yml](file://docker-compose.yml)
- [backend/requirements.txt](file://backend/requirements.txt)
- [frontend/package.json](file://frontend/package.json)
- [backend/app/config.py](file://backend/app/config.py)
- [backend/run.py](file://backend/run.py)
- [frontend/src/main.tsx](file://frontend/src/main.tsx)
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/models/database_config.py](file://backend/app/models/database_config.py)
- [backend/app/models/aws_connection.py](file://backend/app/models/aws_connection.py)
- [backend/app/models/cdc_config.py](file://backend/app/models/cdc_config.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [AWS Integration](#aws-integration)
7. [Creating Your First Migration](#creating-your-first-migration)
8. [Migration Workflows](#migration-workflows)
9. [Monitoring and Observability](#monitoring-and-observability)
10. [Troubleshooting](#troubleshooting)
11. [Next Steps](#next-steps)

## Introduction

CloudBridge is a comprehensive database migration platform designed to streamline schema management and provide Change Data Capture (CDC) capabilities. It serves as a centralized hub for managing database migrations across multiple environments, with built-in approval workflows, real-time monitoring, and AWS integration for cloud-native deployments.

The platform provides both a user-friendly web interface and a robust REST API, enabling teams to collaborate effectively on database changes while maintaining data integrity and consistency across distributed systems.

### Key Features
- **Database Migration Management**: Create, version, and deploy database schema changes
- **Change Data Capture (CDC)**: Real-time data synchronization and replication
- **Approval Workflows**: Multi-stage approval processes for production deployments
- **AWS Integration**: Native support for AWS services including ECS, Secrets Manager, and RDS
- **Real-time Monitoring**: Comprehensive observability and audit logging
- **Multi-environment Support**: Development, staging, and production environment management

## Prerequisites

Before setting up CloudBridge, ensure your system meets the following requirements:

### System Requirements
- **Python 3.8+** for backend development
- **Node.js 16+** for frontend development
- **Docker 20.10+** and **Docker Compose 2.0+** for containerized deployment
- **Git** for version control

### AWS Credentials (Optional)
For full AWS integration features, configure AWS credentials:
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

### Database Requirements
- **PostgreSQL 12+** or **MySQL 8+** for the application database
- **Target databases** for migration operations (any supported database engine)

## Quick Start

### Option 1: Docker Compose (Recommended)

The fastest way to get CloudBridge running is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/cloudbridge/cloudbridge.git
cd cloudbridge

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Option 2: Local Development

#### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the backend server
python run.py
```

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Environment Configuration

### Core Environment Variables

Create a `.env` file in the root directory with the following essential configurations:

#### Application Settings
```env
# Application Configuration
APP_NAME=CloudBridge
APP_ENV=development
DEBUG=True
SECRET_KEY=your-super-secret-key-here

# Server Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/cloudbridge_db
DATABASE_ECHO=False

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

#### Authentication & Security
```env
# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key
JWT_EXPIRATION_HOURS=24
JWT_ALGORITHM=HS256

# OAuth Configuration (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

#### AWS Integration
```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=cloudbridge-artifacts
AWS_SECRETS_MANAGER_ENABLED=True
```

#### CDC Configuration
```env
# CDC Settings
CDC_ENABLED=True
CDC_POLL_INTERVAL=5
CDC_MAX_RETRIES=3
CDC_BATCH_SIZE=1000

# CDC Database Sources
CDC_SOURCE_DB_1_URL=postgresql://source_user:source_pass@source-db:5432/source_db
CDC_TARGET_DB_1_URL=postgresql://target_user:target_pass@target-db:5432/target_db
```

### Configuration File Structure

The application uses a hierarchical configuration system:

```mermaid
flowchart TD
A[Application Start] --> B[Load Default Config]
B --> C[Load Environment Variables]
C --> D{Development Mode?}
D --> |Yes| E[Load .env.development]
D --> |No| F[Load .env.production]
E --> G[Initialize Services]
F --> G
G --> H[Application Ready]
```

**Diagram sources**
- [backend/app/config.py](file://backend/app/config.py)
- [backend/run.py](file://backend/run.py)

**Section sources**
- [backend/app/config.py](file://backend/app/config.py)
- [backend/run.py](file://backend/run.py)

## Database Setup

### Initial Database Creation

CloudBridge requires an initial database to store migration metadata, user accounts, and configuration data.

#### Using Docker Compose
When starting with Docker Compose, the database is automatically provisioned:

```bash
# Start with database service
docker-compose up -d postgres

# Wait for database to be ready
sleep 10

# Initialize application database
docker-compose exec backend alembic upgrade head
```

#### Manual Database Setup
For local development without Docker:

```bash
# Create database
createdb cloudbridge_db

# Create database user
createuser --interactive

# Grant permissions
psql -c "GRANT ALL PRIVILEGES ON DATABASE cloudbridge_db TO cloudbridge_user;"

# Run migrations
alembic upgrade head
```

### Target Database Connections

Configure connections to your target databases for migration operations:

#### PostgreSQL Connection
```json
{
  "name": "production-postgres",
  "type": "postgresql",
  "host": "prod-db.example.com",
  "port": 5432,
  "database": "production_db",
  "username": "migration_user",
  "password": "secure-password",
  "ssl_mode": "require"
}
```

#### MySQL Connection
```json
{
  "name": "staging-mysql",
  "type": "mysql",
  "host": "staging-db.example.com",
  "port": 3306,
  "database": "staging_db",
  "username": "migration_user",
  "password": "secure-password",
  "charset": "utf8mb4"
}
```

**Section sources**
- [backend/app/models/database_config.py](file://backend/app/models/database_config.py)

## AWS Integration

### AWS Service Configuration

CloudBridge integrates with various AWS services to provide cloud-native deployment capabilities.

#### Required AWS Permissions
Ensure your AWS user has the following permissions:
- `ecs:*` - Amazon ECS task management
- `secretsmanager:*` - Secret management
- `s3:*` - Artifact storage
- `logs:*` - CloudWatch Logs access
- `rds:*` - Database management (optional)

#### AWS Configuration via UI
Navigate to **Settings → AWS Configuration** to set up your AWS credentials and region settings.

#### AWS Secrets Manager Integration
Store sensitive configuration in AWS Secrets Manager:

```json
{
  "database_password": "encrypted-password",
  "api_keys": {
    "service_a": "key-a-value",
    "service_b": "key-b-value"
  }
}
```

### ECS Task Configuration

Deploy migrations as ECS tasks for scalable execution:

```json
{
  "task_definition": {
    "family": "cloudbridge-migration",
    "cpu": "256",
    "memory": "512",
    "network_mode": "awsvpc",
    "execution_role_arn": "arn:aws:iam::role/ecs-task-role",
    "container_definitions": [
      {
        "name": "migration-runner",
        "image": "cloudbridge/migration-runner:latest",
        "essential": true,
        "environment": [
          {
            "name": "MIGRATION_JOB_ID",
            "value": "{{job_id}}"
          }
        ]
      }
    ]
  }
}
```

**Section sources**
- [backend/app/models/aws_connection.py](file://backend/app/models/aws_connection.py)

## Creating Your First Migration

### Using the Web Interface

#### Step 1: Access the Dashboard
Open your browser and navigate to `http://localhost:3000`. Log in with your admin credentials.

#### Step 2: Configure Database Connection
1. Go to **Settings → Database Connections**
2. Click **Add New Connection**
3. Enter your database connection details
4. Test the connection
5. Save the configuration

#### Step 3: Create Your First Migration
1. Navigate to **Migrations → Create New**
2. Select your target database connection
3. Choose migration type:
   - **Schema Migration**: For table structure changes
   - **Data Migration**: For data transformations
   - **Seed Data**: For initial data population
4. Write your migration script using the built-in editor
5. Add migration description and tags
6. Click **Create Migration**

#### Step 4: Preview and Validate
1. Review the generated SQL preview
2. Use the validation tool to check syntax
3. Run pre-flight checks against your target database
4. Submit for approval if workflow is enabled

### Using the REST API

#### Create Migration via API
```bash
curl -X POST http://localhost:8000/api/v1/migrations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "add_users_table",
    "description": "Create users table with basic fields",
    "database_connection_id": "conn_123",
    "type": "schema",
    "up_sql": "CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(255));",
    "down_sql": "DROP TABLE IF EXISTS users;",
    "tags": ["users", "core"]
  }'
```

#### List Available Migrations
```bash
curl -X GET http://localhost:8000/api/v1/migrations \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Execute Migration
```bash
curl -X POST http://localhost:8000/api/v1/migrations/mig_123/execute \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Section sources**
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)

## Migration Workflows

### Migration Lifecycle

CloudBridge implements a structured migration lifecycle with multiple stages:

```mermaid
stateDiagram-v2
[*] --> Draft : Create Migration
Draft --> PendingReview : Submit for Review
PendingReview --> Approved : Approve
PendingReview --> Rejected : Reject
Approved --> Scheduled : Schedule Execution
Scheduled --> Executing : Start Execution
Executing --> Success : Complete Successfully
Executing --> Failed : Execution Error
Success --> [*]
Failed --> [*]
Rejected --> Draft : Revise and Resubmit
```

### Approval Process

#### Single-Level Approval
Configure simple approval workflows for development environments:

```json
{
  "workflow": {
    "name": "dev-approval",
    "stages": [
      {
        "name": "developer-review",
        "approvers": ["team-leads"],
        "auto_approve_after_hours": 24
      }
    ]
  }
}
```

#### Multi-Level Approval
Implement complex approval chains for production:

```json
{
  "workflow": {
    "name": "prod-approval",
    "stages": [
      {
        "name": "senior-developer-review",
        "approvers": ["senior-developers"],
        "required_approvals": 2
      },
      {
        "name": "dba-approval",
        "approvers": ["db-admins"],
        "required_approvals": 1
      },
      {
        "name": "security-review",
        "approvers": ["security-team"],
        "required_approvals": 1
      }
    ]
  }
}
```

### Rollback Procedures

Every migration includes automatic rollback capabilities:

```sql
-- Forward Migration
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    total DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Automatic Rollback
DROP TABLE IF EXISTS orders;
```

**Section sources**
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)

## Monitoring and Observability

### Real-time Monitoring

Access the monitoring dashboard at `http://localhost:3000/monitoring` to track:

- **Migration Status**: Real-time progress tracking
- **Database Health**: Connection status and performance metrics
- **System Resources**: CPU, memory, and disk usage
- **Audit Logs**: Complete change history and user actions

### Key Metrics

#### Migration Performance
- Execution time per migration
- Success/failure rates
- Rollback frequency
- Average queue wait times

#### System Health
- Database connection pool utilization
- API response times
- Error rates by endpoint
- Resource consumption trends

### Alerting Configuration

Set up alerts for critical events:

```json
{
  "alerts": {
    "migration_failure": {
      "enabled": true,
      "channels": ["email", "slack"],
      "recipients": ["dba-team@example.com"]
    },
    "high_error_rate": {
      "threshold": 5,
      "window_minutes": 15,
      "notification": "pagerduty"
    }
  }
}
```

### Audit Trail

All actions are logged with complete context:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "user": "john.doe@example.com",
  "action": "migration_execute",
  "resource": "mig_123",
  "details": {
    "migration_name": "add_users_table",
    "target_database": "production-postgres",
    "execution_time_ms": 1250
  },
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0..."
}
```

**Section sources**
- [backend/app/services/observability_service.py](file://backend/app/services/observability_service.py)

## Troubleshooting

### Common Setup Issues

#### Docker Compose Problems
**Issue**: Services fail to start
```bash
# Check service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres

# Verify network connectivity
docker-compose exec backend ping postgres
```

**Solution**: Ensure all required ports are available and Docker daemon is running.

#### Database Connection Errors
**Issue**: Cannot connect to target database
```bash
# Test database connectivity from backend container
docker-compose exec backend python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://user:pass@host:5432/db')
    print('Connection successful')
except Exception as e:
    print(f'Error: {e}')
"
```

**Solution**: Verify firewall rules, SSL certificates, and authentication credentials.

#### AWS Integration Issues
**Issue**: AWS API calls failing
```bash
# Test AWS credentials
docker-compose exec backend aws sts get-caller-identity

# Check IAM permissions
docker-compose exec backend aws iam list-user-policies --user-name your-username
```

**Solution**: Update IAM policies and verify credential configuration.

### Performance Optimization

#### Database Connection Pooling
Adjust connection pool settings for better performance:

```env
# Backend Configuration
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

#### Migration Execution Tuning
Optimize migration execution parameters:

```json
{
  "execution_config": {
    "max_concurrent_migrations": 3,
    "batch_size": 1000,
    "timeout_seconds": 3600,
    "retry_attempts": 3,
    "retry_delay_seconds": 5
  }
}
```

### Debug Mode

Enable detailed debugging for troubleshooting:

```env
# Enable debug logging
DEBUG=True
LOG_LEVEL=DEBUG
SQLALCHEMY_ECHO=True

# Enable detailed error reporting
EXCEPTION_HANDLING_VERBOSE=True
REQUEST_LOGGING_ENABLED=True
```

### Health Checks

Monitor application health endpoints:

```bash
# Backend health check
curl http://localhost:8000/health

# Database connectivity check
curl http://localhost:8000/health/database

# AWS service connectivity
curl http://localhost:8000/health/aws
```

**Section sources**
- [backend/app/routes/health.py](file://backend/app/routes/health.py)

## Next Steps

### Advanced Configuration

Once you have CloudBridge running successfully, explore these advanced features:

#### Custom Migration Templates
Create reusable migration templates for common scenarios:

```python
# Template for adding indexes
def add_index_template(table_name, column_names, index_name=None):
    if not index_name:
        index_name = f"idx_{table_name}_{'_'.join(column_names)}"
    
    return f"""
    CREATE INDEX CONCURRENTLY {index_name} 
    ON {table_name} ({', '.join(column_names)});
    """
```

#### CI/CD Integration
Integrate CloudBridge into your deployment pipeline:

```yaml
# GitHub Actions example
name: Database Migration
on:
  push:
    branches: [main]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run migrations
        run: |
          docker-compose up -d
          docker-compose exec backend alembic upgrade head
```

#### Team Collaboration
Set up team-based access controls and collaboration features through the admin panel.

### Contributing

If you'd like to contribute to CloudBridge development:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Community and Support

- **Documentation**: Visit the official docs site
- **Community Forum**: Join discussions and get help
- **GitHub Issues**: Report bugs and request features
- **Enterprise Support**: Contact for commercial support options

---

**Need Help?** If you encounter any issues during setup or have questions about specific features, please refer to the troubleshooting section above or reach out to the community support channels.