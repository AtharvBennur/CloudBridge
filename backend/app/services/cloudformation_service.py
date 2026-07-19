"""Generate downloadable CloudFormation templates for customer IAM onboarding.

Produces a production-grade, self-contained CloudFormation stack that creates:
  1. CloudBridgeMigrationRole  – cross-account role assumed by CloudBridge backend
     with full infrastructure provisioning permissions.
  2. CloudBridgeExecutionRole  – ECS Fargate execution role (image pull + logs).
  3. CloudBridgeTaskRole       – ECS Fargate task role (runtime AWS access).
"""

from __future__ import annotations

from typing import Any

from flask import current_app

from app.exceptions.aws_connection import (
    AWSConnectionNotFoundError,
    AWSConnectionValidationError,
)
from app.models.aws_connection import AWSConnection


# ---------------------------------------------------------------------------
# Policy fragments – kept as module-level constants for readability.
# ---------------------------------------------------------------------------

_MIGRATION_POLICY_STATEMENTS: list[dict[str, Any]] = [
    # ─ ECS: full management of clusters, tasks, services, definitions ──────
    {
        "Sid": "ECSFullAccess",
        "Effect": "Allow",
        "Action": [
            "ecs:*",
        ],
        "Resource": "*",
    },
    # ── EC2: VPC, subnets, security groups, ENIs, route tables, gateways ────
    {
        "Sid": "EC2FullAccess",
        "Effect": "Allow",
        "Action": [
            "ec2:*",
        ],
        "Resource": "*",
    },
    # ── CloudWatch Logs: create groups, streams, put events ────────────────
    {
        "Sid": "CloudWatchLogsFullAccess",
        "Effect": "Allow",
        "Action": [
            "logs:*",
        ],
        "Resource": "*",
    },
    # ── ECR: pull and manage container images ───────────────────────────────
    {
        "Sid": "ECRFullAccess",
        "Effect": "Allow",
        "Action": [
            "ecr:*",
        ],
        "Resource": "*",
    },
    # ── IAM: create/pass/manage roles for ECS tasks ─────────────────────────
    {
        "Sid": "IAMRoleManagement",
        "Effect": "Allow",
        "Action": [
            "iam:CreateRole",
            "iam:PutRolePolicy",
            "iam:GetRole",
            "iam:GetRolePolicy",
            "iam:PassRole",
            "iam:TagRole",
            "iam:CreateServiceLinkedRole",
            "iam:ListRoles",
            "iam:ListInstanceProfiles",
            "iam:ListRolePolicies",
        ],
        "Resource": "*",
    },
    # ── Secrets Manager: read and write database credentials ──────────────
    {
        "Sid": "SecretsManagerFullAccess",
        "Effect": "Allow",
        "Action": [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret",
            "secretsmanager:CreateSecret",
            "secretsmanager:UpdateSecret",
            "secretsmanager:DeleteSecret",
            "secretsmanager:PutSecretValue",
            "secretsmanager:TagResource",
        ],
        "Resource": "*",
    },
    # ── RDS: discover database instances and clusters ───────────────────────
    {
        "Sid": "RDSReadOnly",
        "Effect": "Allow",
        "Action": [
            "rds:Describe*",
        ],
        "Resource": "*",
    },
    # ── STS: identity verification ──────────────────────────────────────────
    {
        "Sid": "STSIdentity",
        "Effect": "Allow",
        "Action": [
            "sts:GetCallerIdentity",
        ],
        "Resource": "*",
    },
    # ── KMS: decrypt secrets encrypted with customer-managed keys ──────────
    {
        "Sid": "KMSDecrypt",
        "Effect": "Allow",
        "Action": [
            "kms:Decrypt",
            "kms:DescribeKey",
        ],
        "Resource": "*",
    },
    # ── Elastic Load Balancing: manage load balancers and target groups ─────
    {
        "Sid": "ELBFullAccess",
        "Effect": "Allow",
        "Action": [
            "elasticloadbalancing:*",
        ],
        "Resource": "*",
    },
    # ── Application Auto Scaling: scale ECS services ────────────────────────
    {
        "Sid": "AppAutoScalingFullAccess",
        "Effect": "Allow",
        "Action": [
            "application-autoscaling:*",
        ],
        "Resource": "*",
    },
    # ── Service Discovery: Cloud Map namespace / service management ─────────
    {
        "Sid": "ServiceDiscoveryFullAccess",
        "Effect": "Allow",
        "Action": [
            "servicediscovery:*",
        ],
        "Resource": "*",
    },
    # ── CloudWatch Metrics: read/write metrics and alarms ───────────────────
    {
        "Sid": "CloudWatchFullAccess",
        "Effect": "Allow",
        "Action": [
            "cloudwatch:*",
        ],
        "Resource": "*",
    },
    # ── Tagging: tag resources created by CloudBridge ───────────────────────
    {
        "Sid": "TaggingFullAccess",
        "Effect": "Allow",
        "Action": [
            "tag:*",
        ],
        "Resource": "*",
    },
    # ─ Resource Groups: query and manage resource groups ───────────────────
    {
        "Sid": "ResourceGroupsFullAccess",
        "Effect": "Allow",
        "Action": [
            "resource-groups:*",
            "resourcegroupstaggingapi:*",
        ],
        "Resource": "*",
    },
]

_EXECUTION_POLICY_STATEMENTS: list[dict[str, Any]] = [
    {
        "Sid": "ECRImagePull",
        "Effect": "Allow",
        "Action": [
            "ecr:GetAuthorizationToken",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
        ],
        "Resource": "*",
    },
    {
        "Sid": "CloudWatchLogs",
        "Effect": "Allow",
        "Action": [
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "logs:CreateLogGroup",
        ],
        "Resource": "*",
    },
]

_TASK_POLICY_STATEMENTS: list[dict[str, Any]] = [
    {
        "Sid": "SecretsManagerRead",
        "Effect": "Allow",
        "Action": [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret",
        ],
        "Resource": "*",
    },
    {
        "Sid": "SSMRead",
        "Effect": "Allow",
        "Action": [
            "ssm:GetParameter",
            "ssm:GetParameters",
        ],
        "Resource": "*",
    },
]


class CloudFormationService:
    """Builds a CloudFormation template for cross-account IAM onboarding."""

    def generate_template(
        self,
        aws_connection_id: int,
        include_ecs_task_role: bool = True,
    ) -> dict[str, Any]:
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

        # ── Build the template ──────────────────────────────────────────────
        template: dict[str, Any] = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": (
                "CloudBridge production IAM stack - creates the cross-account "
                "migration role, ECS execution role, and ECS task role. "
                "Deploy this stack in the customer AWS account."
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
            },
            "Resources": {
                # ────────────────────────────────────────────────────────────
                # 1. CloudBridgeMigrationRole
                #    Assumed by the CloudBridge backend via sts:AssumeRole.
                #    Grants full infrastructure provisioning permissions so
                #    CloudBridge can auto-create ECS clusters, task definitions,
                #    security groups, subnets, log groups, etc.
                # ────────────────────────────────────────────────────────────
                "CloudBridgeMigrationRole": {
                    "Type": "AWS::IAM::Role",
                    "Properties": {
                        "RoleName": "CloudBridgeMigrationRole",
                        "Description": (
                            "Cross-account role assumed by CloudBridge to "
                            "provision and manage migration infrastructure."
                        ),
                        "AssumeRolePolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {
                                        "AWS": (
                                            f"arn:aws:iam::"
                                            f"{control_plane_account_id}:root"
                                        ),
                                    },
                                    "Action": "sts:AssumeRole",
                                    "Condition": {
                                        "StringEquals": {
                                            "sts:ExternalId": {
                                                "Ref": "ExternalId",
                                            },
                                        },
                                    },
                                },
                            ],
                        },
                        "ManagedPolicyArns": [
                            "arn:aws:iam::aws:policy/ReadOnlyAccess",
                        ],
                        "Policies": [
                            {
                                "PolicyName": "CloudBridgeMigrationPolicy",
                                "PolicyDocument": {
                                    "Version": "2012-10-17",
                                    "Statement": _MIGRATION_POLICY_STATEMENTS,
                                },
                            },
                        ],
                        "Tags": [
                            {
                                "Key": "ManagedBy",
                                "Value": "CloudBridge",
                            },
                            {
                                "Key": "Purpose",
                                "Value": "MigrationOrchestration",
                            },
                        ],
                    },
                },
                # ────────────────────────────────────────────────────────────
                # 2. CloudBridgeExecutionRole
                #    Used by ECS Fargate to pull container images from ECR
                #    and write logs to CloudWatch.  This is the role specified
                #    as executionRoleArn in every task definition.
                # ────────────────────────────────────────────────────────────
                "CloudBridgeExecutionRole": {
                    "Type": "AWS::IAM::Role",
                    "Properties": {
                        "RoleName": "CloudBridgeExecutionRole",
                        "Description": (
                            "ECS Fargate execution role - allows the ECS "
                            "agent to pull images from ECR and write logs "
                            "to CloudWatch Logs."
                        ),
                        "AssumeRolePolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {
                                        "Service": "ecs-tasks.amazonaws.com",
                                    },
                                    "Action": "sts:AssumeRole",
                                },
                            ],
                        },
                        "Policies": [
                            {
                                "PolicyName": "CloudBridgeExecutionPolicy",
                                "PolicyDocument": {
                                    "Version": "2012-10-17",
                                    "Statement": _EXECUTION_POLICY_STATEMENTS,
                                },
                            },
                        ],
                        "Tags": [
                            {
                                "Key": "ManagedBy",
                                "Value": "CloudBridge",
                            },
                            {
                                "Key": "Purpose",
                                "Value": "ECSFargateExecution",
                            },
                        ],
                    },
                },
            },
            "Outputs": {
                "MigrationRoleArn": {
                    "Value": {
                        "Fn::GetAtt": [
                            "CloudBridgeMigrationRole",
                            "Arn",
                        ],
                    },
                    "Description": (
                        "Paste this ARN into CloudBridge as the Role ARN "
                        "for your AWS connection."
                    ),
                    "Export": {
                        "Name": "CloudBridgeMigrationRoleArn",
                    },
                },
                "ExecutionRoleArn": {
                    "Value": {
                        "Fn::GetAtt": [
                            "CloudBridgeExecutionRole",
                            "Arn",
                        ],
                    },
                    "Description": (
                        "ECS Fargate execution role ARN.  Used as "
                        "executionRoleArn in task definitions."
                    ),
                    "Export": {
                        "Name": "CloudBridgeExecutionRoleArn",
                    },
                },
            },
        }

        # ── Optional: ECS Task Role ─────────────────────────────────────────
        #    Used by the running container to access AWS services at runtime
        #    (e.g. reading database credentials from Secrets Manager).
        if include_ecs_task_role:
            template["Resources"]["CloudBridgeTaskRole"] = {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "RoleName": "CloudBridgeTaskRole",
                    "Description": (
                        "ECS Fargate task role - granted to the running "
                        "container so it can read secrets and parameters "
                        "at runtime."
                    ),
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "Service": "ecs-tasks.amazonaws.com",
                                },
                                "Action": "sts:AssumeRole",
                            },
                        ],
                    },
                    "Policies": [
                        {
                            "PolicyName": "CloudBridgeTaskPolicy",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": _TASK_POLICY_STATEMENTS,
                            },
                        },
                    ],
                    "Tags": [
                        {
                            "Key": "ManagedBy",
                            "Value": "CloudBridge",
                        },
                        {
                            "Key": "Purpose",
                            "Value": "ECSFargateTask",
                        },
                    ],
                },
            }
            template["Outputs"]["TaskRoleArn"] = {
                "Value": {
                    "Fn::GetAtt": ["CloudBridgeTaskRole", "Arn"],
                },
                "Description": (
                    "ECS Fargate task role ARN.  Used as taskRoleArn in "
                    "task definitions."
                ),
                "Export": {
                    "Name": "CloudBridgeTaskRoleArn",
                },
            }

        return {
            "aws_connection_id": aws_connection_id,
            "include_ecs_task_role": include_ecs_task_role,
            "template": template,
            "download_filename": f"cloudbridge-iam-{aws_connection_id}.json",
        }
