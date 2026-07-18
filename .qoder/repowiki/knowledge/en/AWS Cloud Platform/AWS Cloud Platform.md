---
kind: external_dependency
name: AWS Cloud Platform
slug: aws
category: external_dependency
category_hints:
    - vendor_identity
    - auth_protocol
scope:
    - '**'
---

### AWS Cloud Platform
- **Role in this repo**: Primary cloud platform for database migration orchestration; CloudBridge uses STS AssumeRole to access customer accounts, Secrets Manager for credential storage, ECS/Fargate for worker execution, CloudWatch for metrics/logs, and Cognito for identity.
- **Integration point**: `backend/app/utils/aws_client.py` provides a thin boto3 wrapper with cross-account AssumeRole flow (role ARN + ExternalId); `backend/app/config.py` centralizes all AWS env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `CLOUDBRIDGE_AWS_ACCOUNT_ID`, `COGNITO_*`).
- **Verify exact API/params against official docs** for STS AssumeRole, Secrets Manager, ECS, CloudWatch, Cognito integration points.