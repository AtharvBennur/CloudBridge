"""Generate downloadable CloudFormation templates for customer AWS onboarding.

Produces a self-contained CloudFormation stack that creates:
  1. CloudBridgeMigrationRole      – cross-account role assumed by the CloudBridge backend
  2. CloudBridgeLambdaExecutionRole – runtime role for Lambda migration functions
  3. Lambda functions, DynamoDB, SQS, and CloudWatch log groups for serverless migrations
"""

from __future__ import annotations

from typing import Any

from flask import current_app

from app.exceptions.aws_connection import (
    AWSConnectionNotFoundError,
    AWSConnectionValidationError,
)
from app.models.aws_connection import AWSConnection


# Minimal inline Lambda code — deploys successfully; replace with production bundles later.
_LAMBDA_PLACEHOLDER_CODE = """import json


def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'success',
            'action': event.get('action'),
            'message': 'CloudBridge Lambda function deployed successfully'
        })
    }
"""


def _lambda_execution_policy_statements() -> list[dict[str, Any]]:
    """Permissions for Lambda functions at runtime inside the customer account."""
    return [
        {
            "Sid": "RDSConnectivity",
            "Effect": "Allow",
            "Action": [
                "rds:DescribeDBInstances",
                "rds:DescribeDBClusters",
                "rds:ListTagsForResource",
            ],
            "Resource": "*",
        },
        {
            "Sid": "SecretsManagerAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:CreateSecret",
                "secretsmanager:UpdateSecret",
                "secretsmanager:PutSecretValue",
                "secretsmanager:TagResource",
            ],
            "Resource": "*",
        },
        {
            "Sid": "KMSDecrypt",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:DescribeKey",
            ],
            "Resource": "*",
        },
        {
            "Sid": "CloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            "Resource": {
                "Fn::Sub": "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/cloudbridge-*",
            },
        },
        {
            "Sid": "SQSAccess",
            "Effect": "Allow",
            "Action": [
                "sqs:SendMessage",
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
            ],
            "Resource": {"Fn::GetAtt": ["MigrationChunkQueue", "Arn"]},
        },
        {
            "Sid": "DynamoDBAccess",
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:DeleteItem",
            ],
            "Resource": [
                {"Fn::GetAtt": ["MigrationMetadataTable", "Arn"]},
                {"Fn::Sub": "${MigrationMetadataTable.Arn}/index/*"},
            ],
        },
        {
            "Sid": "LambdaInvocation",
            "Effect": "Allow",
            "Action": ["lambda:InvokeFunction"],
            "Resource": {
                "Fn::Sub": "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:cloudbridge-migration-worker",
            },
        },
        {
            "Sid": "EC2NetworkAccess",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DeleteNetworkInterface",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeSubnets",
                "ec2:DescribeVpcs",
            ],
            "Resource": "*",
        },
    ]


def _cross_account_policy_statements() -> list[dict[str, Any]]:
    """Permissions granted to the CloudBridge backend after sts:AssumeRole."""
    return [
        {
            "Sid": "STSIdentity",
            "Effect": "Allow",
            "Action": ["sts:GetCallerIdentity"],
            "Resource": "*",
        },
        {
            "Sid": "EC2RegionValidation",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeRegions",
                "ec2:DescribeAvailabilityZones",
            ],
            "Resource": "*",
        },
        {
            "Sid": "LambdaInvoke",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction",
                "lambda:GetFunction",
                "lambda:GetFunctionConfiguration",
            ],
            "Resource": {
                "Fn::Sub": "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:cloudbridge-*",
            },
        },
        {
            "Sid": "SecretsManagerAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecrets",
                "secretsmanager:CreateSecret",
                "secretsmanager:UpdateSecret",
                "secretsmanager:PutSecretValue",
                "secretsmanager:DeleteSecret",
                "secretsmanager:TagResource",
            ],
            "Resource": "*",
        },
        {
            "Sid": "RDSReadOnly",
            "Effect": "Allow",
            "Action": ["rds:Describe*"],
            "Resource": "*",
        },
        {
            "Sid": "DynamoDBAccess",
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan",
            ],
            "Resource": [
                {"Fn::GetAtt": ["MigrationMetadataTable", "Arn"]},
                {"Fn::Sub": "${MigrationMetadataTable.Arn}/index/*"},
            ],
        },
        {
            "Sid": "SQSAccess",
            "Effect": "Allow",
            "Action": [
                "sqs:SendMessage",
                "sqs:ReceiveMessage",
                "sqs:GetQueueAttributes",
            ],
            "Resource": {"Fn::GetAtt": ["MigrationChunkQueue", "Arn"]},
        },
        {
            "Sid": "CloudWatchLogsRead",
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogStreams",
                "logs:GetLogEvents",
                "logs:FilterLogEvents",
            ],
            "Resource": {
                "Fn::Sub": "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/cloudbridge-*",
            },
        },
        {
            "Sid": "PassLambdaExecutionRole",
            "Effect": "Allow",
            "Action": ["iam:PassRole"],
            "Resource": {"Fn::GetAtt": ["CloudBridgeLambdaExecutionRole", "Arn"]},
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "lambda.amazonaws.com",
                },
            },
        },
    ]


def _lambda_function(
    logical_id: str,
    function_name: str,
    description: str,
    timeout: int,
    memory_size: int,
    environment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Lambda function resource with inline placeholder code."""
    env_vars = environment or {}
    properties: dict[str, Any] = {
        "FunctionName": function_name,
        "Description": description,
        "Runtime": "python3.12",
        "Handler": "index.lambda_handler",
        "Role": {"Fn::GetAtt": ["CloudBridgeLambdaExecutionRole", "Arn"]},
        "Timeout": timeout,
        "MemorySize": memory_size,
        "Code": {"ZipFile": _LAMBDA_PLACEHOLDER_CODE},
        "Tags": [
            {"Key": "ManagedBy", "Value": "CloudBridge"},
            {"Key": "Environment", "Value": {"Ref": "Environment"}},
        ],
    }
    if env_vars:
        properties["Environment"] = {"Variables": env_vars}
    return {
        "Type": "AWS::Lambda::Function",
        "DependsOn": [
            "CloudBridgeLambdaExecutionRole",
            f"{logical_id}LogGroup",
        ],
        "Properties": properties,
    }


class CloudFormationService:
    """Builds a CloudFormation template for Lambda-based migration onboarding."""

    def generate_template(self, aws_connection_id: int) -> dict[str, Any]:
        connection = AWSConnection.query.get(aws_connection_id)
        if connection is None:
            raise AWSConnectionNotFoundError(
                f"AWS connection {aws_connection_id} was not found."
            )

        control_plane_account_id = current_app.config.get(
            "CLOUDBRIDGE_AWS_ACCOUNT_ID", ""
        ).strip()
        if not control_plane_account_id:
            raise AWSConnectionValidationError(
                "CLOUDBRIDGE_AWS_ACCOUNT_ID must be configured before "
                "generating an onboarding template. Set it in the backend .env file."
            )

        api_base_url = current_app.config.get("API_BASE_URL", "http://localhost:5000").strip()

        template: dict[str, Any] = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": (
                "CloudBridge Lambda-based migration platform — deploys cross-account "
                "IAM roles, Lambda functions, DynamoDB, and SQS for serverless data migrations."
            ),
            "Parameters": {
                "ExternalId": {
                    "Type": "String",
                    "Description": (
                        "External ID supplied by CloudBridge. "
                        "Used to prevent the confused-deputy problem."
                    ),
                    "Default": connection.external_id,
                },
                "Environment": {
                    "Type": "String",
                    "Default": "production",
                    "AllowedValues": ["development", "staging", "production"],
                    "Description": "Environment name for resource tagging",
                },
                "CloudBridgeAPIURL": {
                    "Type": "String",
                    "Description": "CloudBridge backend API URL used by Lambda functions",
                    "Default": api_base_url,
                },
            },
            "Resources": {
                "MigrationChunkDLQ": {
                    "Type": "AWS::SQS::Queue",
                    "Properties": {
                        "QueueName": "cloudbridge-migration-chunks-dlq",
                        "MessageRetentionPeriod": 1209600,
                        "Tags": [
                            {"Key": "ManagedBy", "Value": "CloudBridge"},
                            {"Key": "Environment", "Value": {"Ref": "Environment"}},
                        ],
                    },
                },
                "MigrationChunkQueue": {
                    "Type": "AWS::SQS::Queue",
                    "DependsOn": ["MigrationChunkDLQ"],
                    "Properties": {
                        "QueueName": "cloudbridge-migration-chunks",
                        "VisibilityTimeout": 900,
                        "MessageRetentionPeriod": 1209600,
                        "RedrivePolicy": {
                            "deadLetterTargetArn": {"Fn::GetAtt": ["MigrationChunkDLQ", "Arn"]},
                            "maxReceiveCount": 5,
                        },
                        "Tags": [
                            {"Key": "ManagedBy", "Value": "CloudBridge"},
                            {"Key": "Environment", "Value": {"Ref": "Environment"}},
                        ],
                    },
                },
                "MigrationMetadataTable": {
                    "Type": "AWS::DynamoDB::Table",
                    "Properties": {
                        "TableName": "cloudbridge-migration-metadata",
                        "BillingMode": "PAY_PER_REQUEST",
                        "AttributeDefinitions": [
                            {"AttributeName": "migration_id", "AttributeType": "S"},
                            {"AttributeName": "chunk_id", "AttributeType": "S"},
                            {"AttributeName": "status", "AttributeType": "S"},
                        ],
                        "KeySchema": [
                            {"AttributeName": "migration_id", "KeyType": "HASH"},
                            {"AttributeName": "chunk_id", "KeyType": "RANGE"},
                        ],
                        "GlobalSecondaryIndexes": [
                            {
                                "IndexName": "StatusIndex",
                                "KeySchema": [
                                    {"AttributeName": "status", "KeyType": "HASH"},
                                ],
                                "Projection": {"ProjectionType": "ALL"},
                            },
                        ],
                        "PointInTimeRecoverySpecification": {
                            "PointInTimeRecoveryEnabled": True,
                        },
                        "Tags": [
                            {"Key": "ManagedBy", "Value": "CloudBridge"},
                            {"Key": "Environment", "Value": {"Ref": "Environment"}},
                        ],
                    },
                },
                "MigrationOrchestratorLogGroup": {
                    "Type": "AWS::Logs::LogGroup",
                    "Properties": {
                        "LogGroupName": "/aws/lambda/cloudbridge-migration-orchestrator",
                        "RetentionInDays": 30,
                    },
                },
                "MigrationWorkerLogGroup": {
                    "Type": "AWS::Logs::LogGroup",
                    "Properties": {
                        "LogGroupName": "/aws/lambda/cloudbridge-migration-worker",
                        "RetentionInDays": 30,
                    },
                },
                "ValidationLogGroup": {
                    "Type": "AWS::Logs::LogGroup",
                    "Properties": {
                        "LogGroupName": "/aws/lambda/cloudbridge-validation",
                        "RetentionInDays": 30,
                    },
                },
                "CloudBridgeLambdaExecutionRole": {
                    "Type": "AWS::IAM::Role",
                    "Properties": {
                        "RoleName": "CloudBridgeLambdaExecutionRole",
                        "Description": (
                            "Runtime role for CloudBridge Lambda migration functions."
                        ),
                        "AssumeRolePolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"Service": "lambda.amazonaws.com"},
                                    "Action": "sts:AssumeRole",
                                },
                            ],
                        },
                        "ManagedPolicyArns": [
                            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                        ],
                        "Policies": [
                            {
                                "PolicyName": "CloudBridgeLambdaExecutionPolicy",
                                "PolicyDocument": {
                                    "Version": "2012-10-17",
                                    "Statement": _lambda_execution_policy_statements(),
                                },
                            },
                        ],
                        "Tags": [
                            {"Key": "ManagedBy", "Value": "CloudBridge"},
                            {"Key": "Purpose", "Value": "LambdaMigrationExecution"},
                        ],
                    },
                },
                "CloudBridgeMigrationRole": {
                    "Type": "AWS::IAM::Role",
                    "DependsOn": [
                        "MigrationMetadataTable",
                        "MigrationChunkQueue",
                        "CloudBridgeLambdaExecutionRole",
                    ],
                    "Properties": {
                        "RoleName": "CloudBridgeMigrationRole",
                        "Description": (
                            "Cross-account role assumed by CloudBridge to orchestrate "
                            "Lambda-based migrations in this AWS account."
                        ),
                        "AssumeRolePolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {
                                        "AWS": f"arn:aws:iam::{control_plane_account_id}:root",
                                    },
                                    "Action": "sts:AssumeRole",
                                    "Condition": {
                                        "StringEquals": {
                                            "sts:ExternalId": {"Ref": "ExternalId"},
                                        },
                                    },
                                },
                            ],
                        },
                        "Policies": [
                            {
                                "PolicyName": "CloudBridgeCrossAccountMigrationPolicy",
                                "PolicyDocument": {
                                    "Version": "2012-10-17",
                                    "Statement": _cross_account_policy_statements(),
                                },
                            },
                        ],
                        "Tags": [
                            {"Key": "ManagedBy", "Value": "CloudBridge"},
                            {"Key": "Purpose", "Value": "LambdaMigrationOrchestration"},
                        ],
                    },
                },
                "MigrationWorkerLambda": _lambda_function(
                    logical_id="MigrationWorker",
                    function_name="cloudbridge-migration-worker",
                    description="Processes individual migration chunks",
                    timeout=900,
                    memory_size=1024,
                    environment={
                        "CLOUDBRIDGE_API_URL": {"Ref": "CloudBridgeAPIURL"},
                        "MIGRATION_METADATA_TABLE": {"Ref": "MigrationMetadataTable"},
                    },
                ),
                "MigrationOrchestratorLambda": _lambda_function(
                    logical_id="MigrationOrchestrator",
                    function_name="cloudbridge-migration-orchestrator",
                    description="Orchestrates migration workflow — schema discovery, chunking, coordination",
                    timeout=900,
                    memory_size=512,
                    environment={
                        "CLOUDBRIDGE_API_URL": {"Ref": "CloudBridgeAPIURL"},
                        "MIGRATION_METADATA_TABLE": {"Ref": "MigrationMetadataTable"},
                        "CHUNK_QUEUE_URL": {"Ref": "MigrationChunkQueue"},
                        "WORKER_LAMBDA_ARN": {"Fn::GetAtt": ["MigrationWorkerLambda", "Arn"]},
                    },
                ),
                "ValidationLambda": _lambda_function(
                    logical_id="Validation",
                    function_name="cloudbridge-validation",
                    description="Validates database connectivity and permissions",
                    timeout=120,
                    memory_size=256,
                    environment={
                        "CLOUDBRIDGE_API_URL": {"Ref": "CloudBridgeAPIURL"},
                    },
                ),
            },
            "Outputs": {
                "MigrationRoleArn": {
                    "Description": (
                        "Paste this ARN into CloudBridge as the Role ARN for your AWS connection."
                    ),
                    "Value": {"Fn::GetAtt": ["CloudBridgeMigrationRole", "Arn"]},
                    "Export": {"Name": "CloudBridgeMigrationRoleArn"},
                },
                "MigrationOrchestratorLambdaArn": {
                    "Description": "ARN of the Migration Orchestrator Lambda function",
                    "Value": {"Fn::GetAtt": ["MigrationOrchestratorLambda", "Arn"]},
                },
                "MigrationWorkerLambdaArn": {
                    "Description": "ARN of the Migration Worker Lambda function",
                    "Value": {"Fn::GetAtt": ["MigrationWorkerLambda", "Arn"]},
                },
                "ValidationLambdaArn": {
                    "Description": "ARN of the Validation Lambda function",
                    "Value": {"Fn::GetAtt": ["ValidationLambda", "Arn"]},
                },
                "MigrationMetadataTableName": {
                    "Description": "DynamoDB table for migration metadata",
                    "Value": {"Ref": "MigrationMetadataTable"},
                },
                "MigrationChunkQueueUrl": {
                    "Description": "SQS queue URL for migration chunks",
                    "Value": {"Ref": "MigrationChunkQueue"},
                },
                "LambdaExecutionRoleArn": {
                    "Description": "Runtime IAM role used by CloudBridge Lambda functions (do not register this in CloudBridge)",
                    "Value": {"Fn::GetAtt": ["CloudBridgeLambdaExecutionRole", "Arn"]},
                },
            },
        }

        # Fix DependsOn log group names to match logical IDs
        for logical_id in ("MigrationOrchestrator", "MigrationWorker", "Validation"):
            fn_key = f"{logical_id}Lambda"
            template["Resources"][fn_key]["DependsOn"] = [
                "CloudBridgeLambdaExecutionRole",
                f"{logical_id}LogGroup",
            ]

        return {
            "aws_connection_id": aws_connection_id,
            "architecture": "lambda",
            "template": template,
            "download_filename": f"cloudbridge-lambda-{aws_connection_id}.json",
        }
