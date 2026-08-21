"""Setup CodeBuild service role for CloudBridge worker image building.

This script creates the necessary IAM service role for AWS CodeBuild
to build and push Docker images to ECR.
"""

import json
import boto3
from botocore.exceptions import ClientError


def create_codebuild_service_role(account_id: str, region: str = "us-east-1") -> str:
    """Create the CodeBuild service role with necessary permissions.
    
    Args:
        account_id: AWS account ID
        region: AWS region
        
    Returns:
        The ARN of the created role
    """
    iam = boto3.client('iam', region_name=region)
    role_name = "codebuild-cloudbridge-service-role"
    
    # Trust policy for CodeBuild
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "codebuild.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Permissions policy for CodeBuild
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ECRPermissions",
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    "ecr:PutImage"
                ],
                "Resource": "*"
            },
            {
                "Sid": "S3Permissions",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::cloudbridge-worker-builds-{account_id}",
                    f"arn:aws:s3:::cloudbridge-worker-builds-{account_id}/*"
                ]
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        # Check if role exists
        iam.get_role(RoleName=role_name)
        print(f"Role {role_name} already exists")
        return f"arn:aws:iam::{account_id}:role/{role_name}"
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchEntity':
            raise
    
    # Create the role
    print(f"Creating CodeBuild service role: {role_name}")
    response = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="CloudBridge CodeBuild service role for Docker image builds",
        Tags=[
            {
                "Key": "ManagedBy",
                "Value": "CloudBridge"
            },
            {
                "Key": "Purpose",
                "Value": "CodeBuildDockerBuilds"
            }
        ]
    )
    
    role_arn = response['Role']['Arn']
    
    # Attach permissions policy
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="CloudBridgeCodeBuildPolicy",
        PolicyDocument=json.dumps(permissions_policy)
    )
    
    print(f"Created CodeBuild service role: {role_arn}")
    return role_arn


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python codebuild_setup.py <account_id> [region]")
        sys.exit(1)
    
    account_id = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "us-east-1"
    
    try:
        role_arn = create_codebuild_service_role(account_id, region)
        print(f"\n✓ CodeBuild service role created successfully: {role_arn}")
        print("\nNext steps:")
        print("1. Deploy the updated CloudFormation template to grant CodeBuild/S3 permissions")
        print("2. The migration system will now automatically build Docker images using CodeBuild")
    except Exception as e:
        print(f"✗ Failed to create CodeBuild service role: {e}")
        sys.exit(1)
