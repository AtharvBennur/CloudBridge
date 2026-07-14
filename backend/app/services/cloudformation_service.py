"""Generate downloadable CloudFormation templates for customer IAM onboarding."""

from __future__ import annotations

from typing import Any

from flask import current_app

from app.models.aws_connection import AWSConnection


class CloudFormationService:
    """Builds a CloudFormation template for cross-account IAM onboarding."""

    def generate_template(self, aws_connection_id: int, include_ecs_task_role: bool = True) -> dict[str, Any]:
        connection = AWSConnection.query.get(aws_connection_id)
        if connection is None:
            raise ValueError(f"AWS connection {aws_connection_id} was not found.")

        control_plane_account_id = current_app.config.get("CLOUDBRIDGE_AWS_ACCOUNT_ID", "").strip()
        if not control_plane_account_id:
            raise ValueError("CLOUDBRIDGE_AWS_ACCOUNT_ID must be configured before generating an onboarding template.")

        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "CloudBridge cross-account IAM role for database migration orchestration",
            "Parameters": {
                "ExternalId": {
                    "Type": "String",
                    "Description": "External ID supplied by CloudBridge",
                    "Default": connection.external_id,
                }
            },
            "Resources": {
                "CloudBridgeMigrationRole": {
                    "Type": "AWS::IAM::Role",
                    "Properties": {
                        "RoleName": "CloudBridgeMigrationRole",
                        "AssumeRolePolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"AWS": f"arn:aws:iam::{control_plane_account_id}:root"},
                                    "Action": "sts:AssumeRole",
                                    "Condition": {"StringEquals": {"sts:ExternalId": {"Ref": "ExternalId"}}},
                                }
                            ],
                        },
                        "Policies": [
                            {
                                "PolicyName": "CloudBridgeMigrationPolicy",
                                "PolicyDocument": {
                                    "Version": "2012-10-17",
                                    "Statement": [
                                        {
                                            "Effect": "Allow",
                                            "Action": [
                                                "secretsmanager:CreateSecret",
                                                "secretsmanager:PutSecretValue",
                                                "secretsmanager:DescribeSecret",
                                                "secretsmanager:GetSecretValue",
                                            ],
                                            "Resource": "*",
                                        },
                                        {
                                            "Effect": "Allow",
                                            "Action": [
                                                "rds:DescribeDBInstances",
                                                "rds:DescribeDBClusters",
                                                "ec2:DescribeRegions",
                                            ],
                                            "Resource": "*",
                                        },
                                    ],
                                },
                            }
                        ],
                    },
                }
            },
            "Outputs": {
                "RoleArn": {
                    "Value": {"Fn::GetAtt": ["CloudBridgeMigrationRole", "Arn"]},
                    "Description": "Role ARN to share with CloudBridge",
                }
            },
        }

        if include_ecs_task_role:
            template["Resources"]["CloudBridgeTaskRole"] = {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "RoleName": "CloudBridgeTaskRole",
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                                "Action": "sts:AssumeRole",
                            }
                        ],
                    },
                    "Policies": [
                        {
                            "PolicyName": "CloudBridgeTaskPolicy",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "secretsmanager:GetSecretValue",
                                            "ssm:GetParameter",
                                        ],
                                        "Resource": "*",
                                    }
                                ],
                            },
                        }
                    ],
                },
            }

        return {
            "aws_connection_id": aws_connection_id,
            "include_ecs_task_role": include_ecs_task_role,
            "template": template,
            "download_filename": f"cloudbridge-iam-{aws_connection_id}.json",
        }
