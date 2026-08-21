"""Discover customer-scoped CloudBridge resources from CloudFormation outputs."""
from __future__ import annotations

from datetime import datetime
from botocore.exceptions import ClientError

from app.extensions import db
from app.models.aws_connection import AWSConnection
from app.utils.aws_client import AWSClient


class InfrastructureDiscoveryError(Exception):
    pass


class InfrastructureDiscoveryService:
    REQUIRED = {"MigrationOrchestratorLambdaArn": "orchestrator_lambda_arn", "MigrationWorkerLambdaArn": "worker_lambda_arn", "ValidationLambdaArn": "validation_lambda_arn", "MigrationMetadataTableName": "dynamodb_table_name"}

    def __init__(self, aws_client: AWSClient | None = None):
        self.aws_client = aws_client or AWSClient()

    def discover(self, aws_connection_id: int, stack_name: str | None = None) -> AWSConnection:
        connection = db.session.get(AWSConnection, aws_connection_id)
        if not connection or not connection.role_arn:
            raise InfrastructureDiscoveryError("AWS connection and assumed-role ARN are required before infrastructure discovery.")
        name = (stack_name or connection.cloudformation_stack_name or "CloudBridgecf").strip()
        try:
            credentials = self.aws_client.assume_role(connection.role_arn, connection.external_id, connection.aws_region)
            cfn = self.aws_client.get_boto3_client("cloudformation", credentials=credentials, region=connection.aws_region)
            stack = cfn.describe_stacks(StackName=name)["Stacks"][0]
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"ValidationError", "ResourceNotFoundException"}:
                raise InfrastructureDiscoveryError("CloudBridge infrastructure stack not found. Deploy infrastructure first.") from exc
            raise InfrastructureDiscoveryError(f"Could not describe CloudBridge infrastructure: {exc}") from exc
        outputs = {item["OutputKey"]: item["OutputValue"] for item in stack.get("Outputs", [])}
        missing = [key for key in self.REQUIRED if not outputs.get(key)]
        if missing:
            raise InfrastructureDiscoveryError("CloudBridge stack exists but required Lambda outputs are missing: " + ", ".join(missing))
        lambda_client = self.aws_client.get_boto3_client("lambda", credentials=credentials, region=connection.aws_region)
        try:
            for key in ("MigrationOrchestratorLambdaArn", "MigrationWorkerLambdaArn", "ValidationLambdaArn"):
                lambda_client.get_function(FunctionName=outputs[key])
            self.aws_client.get_boto3_client("dynamodb", credentials=credentials, region=connection.aws_region).describe_table(TableName=outputs["MigrationMetadataTableName"])
        except ClientError as exc:
            raise InfrastructureDiscoveryError("Infrastructure configuration is stale. Refresh infrastructure.") from exc
        for output, attribute in self.REQUIRED.items():
            setattr(connection, attribute, outputs[output])
        connection.cloudformation_stack_name = name
        connection.infrastructure_discovered_at = datetime.utcnow()
        connection.infrastructure_last_verified_at = datetime.utcnow()
        db.session.commit()
        return connection
