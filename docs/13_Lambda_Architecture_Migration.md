# CloudBridge Lambda Architecture Migration Guide

## Overview

CloudBridge has been migrated from ECS/Fargate to AWS Lambda for serverless data migration execution. This document provides complete deployment instructions and architecture details for the new Lambda-based system.

## Architecture Changes

### Previous Architecture (ECS/Fargate)
```
Frontend → Flask API → ECS/Fargate → CodeBuild/ECR → Worker → Database
```

### New Architecture (Lambda)
```
Frontend → Flask API → Lambda Orchestrator → Lambda Workers → Database
                              ↓
                         DynamoDB (Metadata)
                              ↓
                         SQS (Chunk Queue)
```

## Key Benefits

- **Serverless**: No infrastructure management, automatic scaling
- **Cost-Effective**: Pay only for actual execution time
- **Simpler**: No Docker, CodeBuild, or ECR dependencies
- **Scalable**: Automatic parallel processing via Lambda
- **Resilient**: Built-in retry and error handling

## Components

### 1. Lambda Functions

#### Migration Orchestrator (`cloudbridge-migration-orchestrator`)
- **Purpose**: Coordinates migration workflow
- **Functions**: Schema discovery, chunk creation, coordination
- **Runtime**: Python 3.12
- **Timeout**: 15 minutes
- **Memory**: 512 MB

#### Migration Worker (`cloudbridge-migration-worker`)
- **Purpose**: Processes individual migration chunks
- **Functions**: Data extraction, transformation, loading
- **Runtime**: Python 3.12
- **Timeout**: 15 minutes
- **Memory**: 1024 MB

#### Validation Lambda (`cloudbridge-validation`)
- **Purpose**: Validates database connectivity and permissions
- **Functions**: Connection testing, permission verification
- **Runtime**: Python 3.12
- **Timeout**: 2 minutes
- **Memory**: 256 MB

### 2. Infrastructure Components

#### DynamoDB Table (`cloudbridge-migration-metadata`)
- **Purpose**: Stores migration state and chunk progress
- **Partition Key**: `migration_id`
- **Sort Key**: `chunk_id`
- **Features**: Point-in-time recovery enabled

#### SQS Queue (`cloudbridge-migration-chunks`)
- **Purpose**: Queue for migration chunks
- **Visibility Timeout**: 15 minutes
- **Message Retention**: 14 days
- **DLQ**: `cloudbridge-migration-chunks-dlq`

#### CloudWatch Log Groups
- `/aws/lambda/cloudbridge-migration-orchestrator`
- `/aws/lambda/cloudbridge-migration-worker`
- `/aws/lambda/cloudbridge-validation`

### 3. IAM Role

#### CloudBridgeMigrationRole
- **Trust Policy**: `lambda.amazonaws.com`
- **Permissions**:
  - RDS: DescribeDBInstances, DescribeDBClusters, ListTagsForResource
  - Secrets Manager: GetSecretValue, DescribeSecret
  - KMS: Decrypt, DescribeKey
  - CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents
  - SQS: SendMessage, ReceiveMessage, DeleteMessage, GetQueueAttributes
  - DynamoDB: All operations on migration table
  - Lambda: InvokeFunction (for worker coordination)
  - EC2: Network interface operations (if VPC access needed)

## Deployment Instructions

### Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **AWS CLI**: Installed and configured
3. **Backend URL**: CloudBridge backend API URL (e.g., https://cloudbridge-2-a0fp.onrender.com)
4. **Database Access**: Source and destination databases accessible

### Step 1: Deploy CloudFormation Stack

```bash
# Navigate to infrastructure directory
cd infrastructure

# Deploy the Lambda stack
aws cloudformation create-stack \
  --stack-name cloudbridge-lambda-stack \
  --template-body file://cloudbridge-lambda-stack.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=CloudBridgeAPIURL,ParameterValue=https://cloudbridge-2-a0fp.onrender.com \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### Step 2: Wait for Stack Creation

```bash
# Monitor stack creation
aws cloudformation describe-stacks \
  --stack-name cloudbridge-lambda-stack \
  --region us-east-1
```

Wait until `StackStatus` is `CREATE_COMPLETE`.

### Step 3: Get Stack Outputs

```bash
# Get Lambda ARNs and other outputs
aws cloudformation describe-stacks \
  --stack-name cloudbridge-lambda-stack \
  --query 'Stacks[0].Outputs' \
  --region us-east-1
```

Save the following outputs:
- `MigrationOrchestratorLambdaArn`
- `MigrationWorkerLambdaArn`
- `ValidationLambdaArn`
- `MigrationMetadataTableName`
- `MigrationChunkQueueUrl`
- `CloudBridgeMigrationRoleArn`

### Step 4: Configure Backend Environment Variables

Add the following environment variables to your CloudBridge backend:

```bash
# Lambda ARNs
CLOUDBRIDGE_ORCHESTRATOR_LAMBDA_ARN=<orchestrator-arn-from-outputs>
CLOUDBRIDGE_WORKER_LAMBDA_ARN=<worker-arn-from-outputs>
CLOUDBRIDGE_VALIDATION_LAMBDA_ARN=<validation-arn-from-outputs>

# Infrastructure
CLOUDBRIDGE_DYNAMODB_TABLE=<table-name-from-outputs>
CLOUDBRIDGE_SQS_QUEUE_URL=<queue-url-from-outputs>

# AWS Region
AWS_REGION=us-east-1
```

### Step 5: Update Database Schema

The new architecture requires additional database tables. Run the migration:

```bash
cd backend
python -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database schema updated')"
```

### Step 6: Restart Backend

Restart your CloudBridge backend to load the new environment variables and code.

```bash
# If using Render.com
# Push changes and Render will auto-deploy
git add .
git commit -m "Deploy Lambda architecture"
git push
```

### Step 7: Verify Deployment

1. **Check Lambda Functions**:
   ```bash
   aws lambda list-functions --region us-east-1 | grep cloudbridge
   ```

2. **Check DynamoDB Table**:
   ```bash
   aws dynamodb describe-table \
     --table-name cloudbridge-migration-metadata \
     --region us-east-1
   ```

3. **Check SQS Queue**:
   ```bash
   aws sqs get-queue-attributes \
     --queue-url <queue-url-from-outputs> \
     --attribute-names All \
     --region us-east-1
   ```

4. **Test Validation Lambda**:
   ```bash
   aws lambda invoke \
     --function-name <validation-lambda-arn> \
     --payload '{"db_type":"mysql","config":{"host":"test","port":3306,"username":"test","password":"test","database_name":"test"},"validation_type":"source"}' \
     --region us-east-1 \
     response.json
   ```

## Migration Workflow

### 1. Create Migration
- User creates migration job via UI
- Backend validates source/destination databases
- Lambda validation function performs real connectivity checks

### 2. Start Migration
- Backend invokes Lambda orchestrator
- Orchestrator discovers source schema
- Schema is analyzed and chunked
- Chunks are sent to SQS queue

### 3. Process Chunks
- Lambda workers pull chunks from SQS
- Each worker processes one chunk
- Progress is written to DynamoDB
- Failed chunks go to DLQ for retry

### 4. Monitor Progress
- Backend polls DynamoDB for progress
- WebSocket updates sent to UI
- Real-time progress displayed

### 5. Complete Migration
- All chunks processed successfully
- Verification Lambda validates data integrity
- Migration marked as completed

## Files Changed

### Backend Files

**New Files:**
- `backend/app/services/lambda_migration_service.py` - Lambda migration orchestration
- `backend/app/models/lambda_migration.py` - Lambda migration tracking models
- `backend/app/services/schema_discovery_service.py` - Schema discovery logic
- `backend/app/services/data_migration_service.py` - Data migration logic

**Modified Files:**
- `backend/app/routes/migration_engine.py` - Updated to use Lambda instead of ECS
- `backend/app/services/cloudformation_service.py` - Updated IAM permissions

**Deleted Files:**
- `backend/app/exceptions/ecs.py`
- `backend/app/models/ecs_task.py`
- `backend/app/routes/ecs.py`
- `backend/app/schemas/ecs.py`
- `backend/app/services/ecs_manager.py`
- `backend/app/services/ecs_resource_discovery.py`
- `backend/app/services/ecs_service.py`
- `backend/app/services/ecs_task_definition.py`
- `backend/app/services/ecr_manager.py`
- `backend/app/services/migration_execution_service.py`
- `backend/app/services/codebuild_setup.py`

### Frontend Files

**Modified Files:**
- `frontend/src/App.tsx` - Removed ECS route
- `frontend/src/components/layout/Sidebar.tsx` - Replaced ECS with Lambda Functions
- `frontend/src/pages/DashboardPage.tsx` - Updated to reflect Lambda architecture

**Deleted Files:**
- `frontend/src/services/ecsService.ts`
- `frontend/src/pages/ECSPage.tsx`

### Infrastructure Files

**New Files:**
- `infrastructure/cloudbridge-lambda-stack.yaml` - Complete Lambda CloudFormation template

**Deleted Files:**
- `docs/12_CodeBuild_Setup.md`

## Environment Variables Required

### Backend
```
CLOUDBRIDGE_ORCHESTRATOR_LAMBDA_ARN=arn:aws:lambda:us-east-1:123456789012:function:cloudbridge-migration-orchestrator
CLOUDBRIDGE_WORKER_LAMBDA_ARN=arn:aws:lambda:us-east-1:123456789012:function:cloudbridge-migration-worker
CLOUDBRIDGE_VALIDATION_LAMBDA_ARN=arn:aws:lambda:us-east-1:123456789012:function:cloudbridge-validation
CLOUDBRIDGE_DYNAMODB_TABLE=cloudbridge-migration-metadata
CLOUDBRIDGE_SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/cloudbridge-migration-chunks
AWS_REGION=us-east-1
```

## Testing

### 1. Test Database Validation
```bash
curl -X POST https://your-backend.com/api/database-configs/validate \
  -H "Content-Type: application/json" \
  -d '{
    "database_type": "mysql",
    "host": "your-db-host",
    "port": 3306,
    "username": "your-user",
    "password": "your-password",
    "database_name": "your-db",
    "purpose": "SOURCE"
  }'
```

### 2. Test Migration Creation
```bash
curl -X POST https://your-backend.com/api/migrations \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "Test Migration",
    "source_database_config_id": 1,
    "destination_database_config_id": 2,
    "aws_connection_id": 1
  }'
```

### 3. Test Migration Start
```bash
curl -X POST https://your-backend.com/api/migration-engine/start \
  -H "Content-Type: application/json" \
  -d '{
    "migration_id": 1,
    "aws_connection_id": 1
  }'
```

### 4. Monitor Progress
```bash
curl https://your-backend.com/api/migration-engine/1/status
```

## Troubleshooting

### Lambda Timeout
- **Issue**: Lambda functions timing out
- **Solution**: Increase timeout in CloudFormation template or reduce chunk size

### Memory Issues
- **Issue**: Lambda out of memory errors
- **Solution**: Increase memory allocation in CloudFormation template

### SQS Queue Not Processing
- **Issue**: Chunks stuck in queue
- **Solution**: Check Lambda worker logs, verify IAM permissions

### DynamoDB Throttling
- **Issue**: DynamoDB write throttling
- **Solution**: Enable auto-scaling or use on-demand capacity mode

### Connection Failures
- **Issue**: Database connection failures
- **Solution**: Check security groups, VPC configuration, and database accessibility

## Rollback Procedure

If you need to rollback to the ECS architecture:

1. **Delete Lambda Stack**:
   ```bash
   aws cloudformation delete-stack \
     --stack-name cloudbridge-lambda-stack \
     --region us-east-1
   ```

2. **Restore Backend Code**:
   ```bash
   git checkout <commit-before-migration>
   ```

3. **Restore Frontend Code**:
   ```bash
   git checkout <commit-before-migration>
   ```

4. **Remove Environment Variables**:
   Delete Lambda-related environment variables from backend

5. **Restart Services**:
   Restart backend and frontend

## Cost Considerations

### Lambda Costs
- **Orchestrator**: ~$0.000000208 per 100ms (512 MB)
- **Worker**: ~$0.000000416 per 100ms (1 GB)
- **Validation**: ~$0.000000208 per 100ms (256 MB)

### DynamoDB Costs
- **On-Demand**: $1.25 per million write units, $0.25 per million read units
- **Storage**: $0.25 per GB-month

### SQS Costs
- **Standard Queue**: $0.40 per million requests
- **Data Transfer**: Varies by region

**Estimated Monthly Cost**: $10-50 for moderate usage (100 migrations)

## Security Considerations

1. **IAM Roles**: Use least privilege principle
2. **Secrets Manager**: Store database credentials securely
3. **VPC**: Consider VPC configuration for database access
4. **Encryption**: Enable encryption at rest and in transit
5. **Logging**: Monitor CloudWatch logs for security events

## Monitoring

### CloudWatch Metrics
- Lambda invocation count
- Lambda duration
- Lambda error rate
- DynamoDB consumed capacity
- SQS queue depth

### CloudWatch Logs
- Lambda function logs
- Error logs
- Performance metrics

### Alarms
- Lambda error rate > 5%
- SQS queue depth > 1000
- Lambda duration > 10 minutes

## Next Steps

1. **Deploy the CloudFormation stack** using the instructions above
2. **Configure environment variables** in your backend
3. **Test the migration workflow** with a small test database
4. **Monitor CloudWatch logs** for any issues
5. **Scale up** to production migrations

## Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Review this troubleshooting section
3. Verify IAM permissions
4. Check database connectivity
5. Review Lambda function configuration

## Architecture Summary

The new Lambda-based architecture provides:
- **Serverless execution** with automatic scaling
- **Cost optimization** with pay-per-use pricing
- **Simplified operations** with no Docker/ECR management
- **Improved reliability** with built-in retry mechanisms
- **Better monitoring** with CloudWatch integration

The migration from ECS to Lambda is complete and ready for production use.
