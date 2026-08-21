# CodeBuild Setup for Automated Docker Image Building

## Overview

CloudBridge now uses AWS CodeBuild to build and push Docker images to ECR automatically, eliminating the need for local Docker Desktop. This enables fully automated migration execution from the Render.com hosted environment.

## Architecture

```
CloudBridge (Render.com)
    ↓
1. Uploads worker source to S3
    ↓
2. Triggers CodeBuild project
    ↓
3. CodeBuild builds Docker image
    ↓
4. CodeBuild pushes image to ECR
    ↓
5. ECS pulls image from ECR
```

## Prerequisites

- AWS account with appropriate IAM permissions
- CloudBridge backend deployed on Render.com
- Existing CloudBridge IAM role (from CloudFormation template)

## Setup Steps

### Step 1: Create CodeBuild Service Role

Run the setup script from your local machine:

```bash
cd backend
python -m app.services.codebuild_setup 482314592899 us-east-1
```

Replace `482314592899` with your AWS account ID and `us-east-1` with your region.

This creates the `codebuild-cloudbridge-service-role` with permissions to:
- Access ECR for pulling/pushing images
- Access S3 for retrieving source code
- Write logs to CloudWatch

### Step 2: Update CloudFormation Template

Deploy the updated CloudFormation template to grant CodeBuild and S3 permissions to your CloudBridge migration role:

1. Go to CloudBridge UI → AWS Connections
2. Select your connection
3. Click "Download CloudFormation Template"
4. Deploy the template in your AWS account via CloudFormation Console

The updated template includes:
- `codebuild:*` permissions for managing builds
- `s3:*` permissions for `cloudbridge-worker-builds-*` buckets

### Step 3: Verify Setup

Test the automated build by starting a migration:

1. Create a migration job in CloudBridge
2. Start the migration
3. Monitor the logs - you should see:
   - "Uploaded worker source to S3"
   - "Triggered CodeBuild build"
   - "CodeBuild completed successfully"
   - "ECS task launched successfully"

## How It Works

### 1. Source Upload
- CloudBridge zips the worker directory
- Uploads to S3 bucket: `cloudbridge-worker-builds-{account_id}`
- Key: `worker-source.zip`

### 2. CodeBuild Project
- Project name: `cloudbridge-worker-builder`
- Source: S3 bucket with uploaded zip
- Environment: `aws/codebuild/standard:7.0` with privileged mode
- Buildspec:
  - Install Docker
  - Login to ECR
  - Build image
  - Push to ECR

### 3. Image Tagging
- Images are tagged with content hash: `sha-{hash}`
- Also tagged as `:latest` for ECS task definitions
- Content hash ensures rebuilds only when code changes

### 4. Infrastructure Auto-Creation
The system automatically creates:
- ECR repository: `cloudbridge-migration-worker`
- S3 bucket: `cloudbridge-worker-builds-{account_id}`
- CodeBuild project: `cloudbridge-worker-builder`

## Troubleshooting

### CodeBuild Role Not Found

Error: `AccessDenied: User is not authorized to perform: codebuild:CreateProject`

**Solution**: Ensure the CodeBuild service role exists:
```bash
python -m app.services.codebuild_setup 482314592899 us-east-1
```

### S3 Access Denied

Error: `AccessDenied: Access Denied` when uploading to S3

**Solution**: Update CloudFormation template to include S3 permissions for the CloudBridge migration role.

### ECR Push Failed

Error: `CodeBuild build failed with status FAILED`

**Solution**: Check CloudBuild logs in AWS Console:
1. Go to CodeBuild → Build projects → cloudbridge-worker-builder
2. View build logs for detailed error messages
3. Common issues:
   - ECR repository doesn't exist (auto-created, but may fail)
   - Docker build syntax errors in worker/Dockerfile
   - Network connectivity issues

### Build Timeout

Error: `CodeBuild build timed out after 600s`

**Solution**: 
- Increase timeout in `ecr_manager.py` line 408
- Optimize Dockerfile for faster builds
- Check if worker directory has unnecessary large files

## Cost Considerations

- **CodeBuild**: ~$0.005/minute for BUILD_GENERAL1_SMALL
- **S3 Storage**: ~$0.023/GB/month for source zip
- **ECR Storage**: ~$0.10/GB/month for Docker images

Typical migration build: 2-5 minutes = $0.01-$0.025 per build

## Security

- CodeBuild service role has least-privilege access
- S3 bucket is scoped to specific CloudBridge account
- ECR repository uses AWS-managed encryption
- No credentials stored in code or environment variables

## Monitoring

View CodeBuild logs in AWS Console:
```
CodeBuild → Build projects → cloudbridge-worker-builder → Build history
```

View ECR images:
```
ECR → Repositories → cloudbridge-migration-worker → Images
```

## Rollback

To revert to local Docker builds (if needed):

1. Restore original `ecr_manager.py` from git
2. Ensure Docker Desktop is running on the machine running CloudBridge
3. Restart the backend service

## Next Steps

After setup:
1. Test with a small migration
2. Monitor CodeBuild build times
3. Set up CloudWatch alarms for build failures
4. Consider using CodeBuild caching for faster builds
