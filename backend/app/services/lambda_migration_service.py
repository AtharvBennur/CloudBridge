"""Lambda Migration Service — orchestrates serverless migration execution.

This service replaces the ECS/Fargate architecture with AWS Lambda for
serverless data migration execution.

Flow:
  Start Migration
    ↓
  Validate Source/Destination Databases
    ↓
  Discover Source Schema
    ↓
  Create Destination Schema
    ↓
  Calculate Migration Workload
    ↓
  Split Work into Chunks
    ↓
  Invoke Lambda Orchestrator
    ↓
  Lambda Processes Chunks
    ↓
  Persist Progress to DynamoDB
    ↓
  Monitor and Retry Failures
    ↓
  Verify Migrated Data
    ↓
  Mark Migration Completed
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from flask import current_app
from botocore.exceptions import ClientError

from app.extensions import db
from app.models.aws_connection import AWSConnection
from app.models.database_config import DatabaseConfig
from app.models.migration import MigrationJob, MigrationStatus
from app.models.lambda_migration import LambdaMigration, LambdaMigrationStatus, LambdaChunk
from app.exceptions.migration import MigrationError, lambda_execution_error, lambda_validation_error
from app.services.websocket_service import websocket_service
from app.utils.aws_client import AWSClient

logger = logging.getLogger(__name__)


@dataclass
class MigrationChunk:
    """Represents a single chunk of work for migration."""
    chunk_id: str
    table_name: str
    start_row: int
    end_row: int
    estimated_rows: int
    status: str = "PENDING"


@dataclass
class SchemaInfo:
    """Represents database schema information."""
    tables: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, Any]]


class LambdaMigrationService:
    """Orchestrates Lambda-based migration execution."""

    def __init__(self, aws_client: AWSClient | None = None) -> None:
        self._aws_client = aws_client or AWSClient()

    def prepare_migration(
        self,
        migration_id: int,
        aws_connection_id: int | None = None,
    ) -> LambdaMigration:
        """Validate inputs and create a PENDING Lambda migration record.

        Returns the LambdaMigration record quickly so the HTTP request can return 202.
        """
        migration = MigrationJob.query.get(migration_id)
        if not migration:
            raise MigrationError(f"Migration job {migration_id} was not found.")

        if migration.status in {MigrationStatus.RUNNING, MigrationStatus.COMPLETED}:
            raise MigrationError(
                f"Migration cannot be started from status '{migration.status}'."
            )

        # Validate database configs
        if not migration.source_database_config_id:
            raise MigrationError("Migration job has no source database configuration linked.")
        if not migration.destination_database_config_id:
            raise MigrationError("Migration job has no destination database configuration linked.")

        src = DatabaseConfig.query.get(migration.source_database_config_id)
        dst = DatabaseConfig.query.get(migration.destination_database_config_id)
        
        if src and not src.database_name:
            raise MigrationError(f"Source database config '{src.name}' has no database_name set.")
        if dst and not dst.database_name:
            raise MigrationError(f"Destination database config '{dst.name}' has no database_name set.")

        # Resolve AWS connection (request payload → migration → linked database configs)
        effective_connection_id = (
            aws_connection_id
            or migration.aws_connection_id
            or (src.aws_connection_id if src else None)
            or (dst.aws_connection_id if dst else None)
        )
        aws_connection = AWSConnection.query.get(effective_connection_id)
        if not aws_connection or not aws_connection.role_arn:
            raise MigrationError("No valid AWS connection found.")

        if migration.aws_connection_id != aws_connection.id:
            migration.aws_connection_id = aws_connection.id

        # Create Lambda migration record
        lambda_migration = LambdaMigration(
            migration_id=migration.id,
            aws_connection_id=aws_connection.id,
            status=LambdaMigrationStatus.PENDING,
            orchestrator_arn="",
            worker_arn="",
            chunks_created=0,
            chunks_completed=0,
            chunks_failed=0,
            rows_migrated=0,
            error_message=None,
        )
        db.session.add(lambda_migration)

        # Mark migration as running
        migration.status = MigrationStatus.RUNNING
        migration.started_at = datetime.utcnow()
        db.session.commit()

        websocket_service.broadcast_migration_update(
            migration.id,
            {
                "status": MigrationStatus.RUNNING,
                "message": "Migration preparing for Lambda execution…",
            },
        )

        return lambda_migration

    def execute_migration_background(
        self,
        app,
        lambda_migration_id: int,
        migration_id: int,
        aws_connection_id: int,
    ) -> None:
        """Run the full Lambda migration flow in a background thread."""
        with app.app_context():
            try:
                self._do_execute(lambda_migration_id, migration_id, aws_connection_id)
            except Exception as exc:
                logger.exception(
                    "Background Lambda migration execution failed",
                    exc_info=True,
                    extra={
                        "lambda_migration_id": lambda_migration_id,
                        "migration_id": migration_id,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )
                # Mark as failed
                lambda_migration = db.session.get(LambdaMigration, lambda_migration_id)
                migration = db.session.get(MigrationJob, migration_id)
                if lambda_migration:
                    lambda_migration.status = LambdaMigrationStatus.FAILED
                    lambda_migration.error_message = str(exc)
                if migration:
                    migration.status = MigrationStatus.FAILED
                    migration.error_message = str(exc)
                db.session.commit()

    def _do_execute(
        self,
        lambda_migration_id: int,
        migration_id: int,
        aws_connection_id: int,
    ) -> None:
        """Internal execution logic for Lambda migration."""
        lambda_migration = db.session.get(LambdaMigration, lambda_migration_id)
        migration = db.session.get(MigrationJob, migration_id)
        aws_connection = db.session.get(AWSConnection, aws_connection_id)

        if not lambda_migration or not migration or not aws_connection:
            raise MigrationError("Lambda migration, migration, or AWS connection not found.")

        # Assume role
        try:
            credentials = self._aws_client.assume_role(
                aws_connection.role_arn,
                aws_connection.external_id,
                aws_connection.aws_region,
            )
        except ValueError as exc:
            raise lambda_execution_error(
                f"Cannot assume AWS role: {exc}"
            ) from exc

        # Initialize AWS clients
        lambda_client = self._aws_client.get_boto3_client("lambda", credentials=credentials, region=aws_connection.aws_region)
        dynamodb_client = self._aws_client.get_boto3_client("dynamodb", credentials=credentials, region=aws_connection.aws_region)

        # Step 1: Validate databases
        self._validate_databases(migration, lambda_client)

        # Step 2: Discover schema
        schema = self._discover_schema(migration, lambda_client)

        # Step 3: Create chunks
        chunks = self._create_chunks(migration, schema)

        # Step 4: Invoke orchestrator
        self._invoke_orchestrator(lambda_migration, migration, chunks, lambda_client)

        # Step 5: Monitor execution
        self._monitor_execution(lambda_migration, migration, dynamodb_client)

        # Step 6: Verify migration
        self._verify_migration(migration, lambda_client)

        # Mark as completed
        lambda_migration.status = LambdaMigrationStatus.COMPLETED
        migration.status = MigrationStatus.COMPLETED
        migration.completed_at = datetime.utcnow()
        db.session.commit()

        websocket_service.broadcast_migration_update(
            migration.id,
            {"status": MigrationStatus.COMPLETED, "message": "Migration completed successfully"},
        )

    def _validate_databases(self, migration: MigrationJob, lambda_client: Any) -> None:
        """Validate source and destination database connectivity."""
        logger.info("Validating databases for migration %d", migration.id)

        src_config = DatabaseConfig.query.get(migration.source_database_config_id)
        dst_config = DatabaseConfig.query.get(migration.destination_database_config_id)

        # Get Lambda ARN from environment or CloudFormation outputs
        validator_arn = os.environ.get("CLOUDBRIDGE_VALIDATION_LAMBDA_ARN")
        if not validator_arn:
            raise lambda_validation_error("Validation Lambda ARN not configured")

        # Validate source
        src_payload = {
            "db_type": src_config.database_type,
            "config": {
                "host": src_config.host,
                "port": src_config.port,
                "username": src_config.username,
                "password": src_config.password,
                "database_name": src_config.database_name,
            },
            "validation_type": "source"
        }

        try:
            response = lambda_client.invoke(
                FunctionName=validator_arn,
                InvocationType="RequestResponse",
                Payload=json.dumps(src_payload)
            )
            result = json.loads(response["Payload"].read())
            
            if result.get("status") != "success":
                raise lambda_validation_error(f"Source database validation failed: {result.get('error')}")
            
            logger.info("Source database validation successful")
        except ClientError as exc:
            raise lambda_validation_error(f"Failed to invoke validation Lambda: {exc}") from exc

        # Validate destination
        dst_payload = {
            "db_type": dst_config.database_type,
            "config": {
                "host": dst_config.host,
                "port": dst_config.port,
                "username": dst_config.username,
                "password": dst_config.password,
                "database_name": dst_config.database_name,
            },
            "validation_type": "destination"
        }

        try:
            response = lambda_client.invoke(
                FunctionName=validator_arn,
                InvocationType="RequestResponse",
                Payload=json.dumps(dst_payload)
            )
            result = json.loads(response["Payload"].read())
            
            if result.get("status") != "success":
                raise lambda_validation_error(f"Destination database validation failed: {result.get('error')}")
            
            logger.info("Destination database validation successful")
        except ClientError as exc:
            raise lambda_validation_error(f"Failed to invoke validation Lambda: {exc}") from exc

    def _discover_schema(self, migration: MigrationJob, lambda_client: Any) -> SchemaInfo:
        """Discover source database schema."""
        logger.info("Discovering schema for migration %d", migration.id)

        orchestrator_arn = os.environ.get("CLOUDBRIDGE_ORCHESTRATOR_LAMBDA_ARN")
        if not orchestrator_arn:
            raise lambda_execution_error("Orchestrator Lambda ARN not configured")

        src_config = DatabaseConfig.query.get(migration.source_database_config_id)

        payload = {
            "action": "discover_schema",
            "migration_id": migration.id,
            "source_config": {
                "db_type": src_config.database_type,
                "host": src_config.host,
                "port": src_config.port,
                "username": src_config.username,
                "password": src_config.password,
                "database_name": src_config.database_name,
            }
        }

        try:
            response = lambda_client.invoke(
                FunctionName=orchestrator_arn,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload)
            )
            result = json.loads(response["Payload"].read())
            
            if result.get("status") != "success":
                raise lambda_execution_error(f"Schema discovery failed: {result.get('error')}")
            
            schema = result.get("schema", {})
            logger.info("Schema discovery completed: %d tables", len(schema.get("tables", [])))
            
            return SchemaInfo(
                tables=schema.get("tables", []),
                indexes=schema.get("indexes", []),
                foreign_keys=schema.get("foreign_keys", [])
            )
        except ClientError as exc:
            raise lambda_execution_error(f"Failed to invoke orchestrator Lambda: {exc}") from exc

    def _create_chunks(self, migration: MigrationJob, schema: SchemaInfo) -> List[MigrationChunk]:
        """Create migration chunks based on schema and data size."""
        logger.info("Creating chunks for migration %d", migration.id)

        chunks = []
        chunk_id = 0

        for table in schema.tables:
            table_name = table["name"]
            estimated_rows = table.get("estimated_rows", 0)
            
            # Calculate chunk size (max 100,000 rows per chunk for Lambda limits)
            chunk_size = min(100000, max(1000, estimated_rows // 10))
            
            if estimated_rows > 0:
                num_chunks = (estimated_rows + chunk_size - 1) // chunk_size
            else:
                num_chunks = 1

            for i in range(num_chunks):
                start_row = i * chunk_size
                end_row = min((i + 1) * chunk_size - 1, estimated_rows - 1) if estimated_rows > 0 else 0
                
                chunk = MigrationChunk(
                    chunk_id=f"{migration.id}-{table_name}-{i}",
                    table_name=table_name,
                    start_row=start_row,
                    end_row=end_row,
                    estimated_rows=min(chunk_size, estimated_rows - start_row) if estimated_rows > 0 else 0,
                )
                chunks.append(chunk)
                chunk_id += 1

        logger.info("Created %d chunks for migration", len(chunks))
        return chunks

    def _invoke_orchestrator(
        self,
        lambda_migration: LambdaMigration,
        migration: MigrationJob,
        chunks: List[MigrationChunk],
        lambda_client: Any
    ) -> None:
        """Invoke Lambda orchestrator to start chunk processing."""
        logger.info("Invoking orchestrator for migration %d", migration.id)

        orchestrator_arn = os.environ.get("CLOUDBRIDGE_ORCHESTRATOR_LAMBDA_ARN")
        if not orchestrator_arn:
            raise lambda_execution_error("Orchestrator Lambda ARN not configured")

        src_config = DatabaseConfig.query.get(migration.source_database_config_id)
        dst_config = DatabaseConfig.query.get(migration.destination_database_config_id)

        payload = {
            "action": "coordinate_migration",
            "migration_id": migration.id,
            "lambda_migration_id": lambda_migration.id,
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "table_name": chunk.table_name,
                    "start_row": chunk.start_row,
                    "end_row": chunk.end_row,
                    "estimated_rows": chunk.estimated_rows,
                }
                for chunk in chunks
            ],
            "source_config": {
                "db_type": src_config.database_type,
                "host": src_config.host,
                "port": src_config.port,
                "username": src_config.username,
                "password": src_config.password,
                "database_name": src_config.database_name,
            },
            "dest_config": {
                "db_type": dst_config.database_type,
                "host": dst_config.host,
                "port": dst_config.port,
                "username": dst_config.username,
                "password": dst_config.password,
                "database_name": dst_config.database_name,
            }
        }

        try:
            response = lambda_client.invoke(
                FunctionName=orchestrator_arn,
                InvocationType="Event",  # Async invocation
                Payload=json.dumps(payload)
            )
            
            lambda_migration.status = LambdaMigrationStatus.RUNNING
            lambda_migration.chunks_created = len(chunks)
            lambda_migration.orchestrator_arn = orchestrator_arn
            db.session.commit()
            
            logger.info("Orchestrator invoked successfully")
        except ClientError as exc:
            raise lambda_execution_error(f"Failed to invoke orchestrator Lambda: {exc}") from exc

    def _monitor_execution(
        self,
        lambda_migration: LambdaMigration,
        migration: MigrationJob,
        dynamodb_client: Any
    ) -> None:
        """Monitor Lambda execution progress via DynamoDB."""
        logger.info("Monitoring execution for migration %d", migration.id)

        table_name = os.environ.get("CLOUDBRIDGE_DYNAMODB_TABLE", "cloudbridge-migration-metadata")
        
        import time
        timeout = 3600  # 1 hour timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Query DynamoDB for chunk status
            try:
                response = dynamodb_client.query(
                    TableName=table_name,
                    KeyConditionExpression="migration_id = :mid",
                    ExpressionAttributeValues={":mid": str(migration.id)}
                )
                
                items = response.get("Items", [])
                completed = sum(1 for item in items if item.get("status") == "COMPLETED")
                failed = sum(1 for item in items if item.get("status") == "FAILED")
                total = len(items)
                
                # Update progress
                lambda_migration.chunks_completed = completed
                lambda_migration.chunks_failed = failed
                
                if total > 0:
                    progress = (completed / total) * 100
                    migration.progress_percent = progress
                    migration.rows_migrated = completed * 1000  # Placeholder - should come from actual data
                
                db.session.commit()
                
                # Broadcast progress
                websocket_service.broadcast_migration_update(
                    migration.id,
                    {
                        "status": MigrationStatus.RUNNING,
                        "progress": progress if total > 0 else 0,
                        "chunks_completed": completed,
                        "chunks_failed": failed,
                        "total_chunks": total,
                    }
                )
                
                # Check if all chunks are done
                if completed + failed == total and total > 0:
                    if failed > 0:
                        raise lambda_execution_error(f"{failed} chunks failed during migration")
                    logger.info("All chunks completed successfully")
                    break
                
                time.sleep(10)  # Poll every 10 seconds
                
            except ClientError as exc:
                logger.warning("Failed to query DynamoDB: %s", exc)
                time.sleep(5)
        
        if time.time() - start_time >= timeout:
            raise lambda_execution_error("Migration monitoring timed out")

    def _verify_migration(self, migration: MigrationJob, lambda_client: Any) -> None:
        """Verify migrated data integrity."""
        logger.info("Verifying migration %d", migration.id)

        orchestrator_arn = os.environ.get("CLOUDBRIDGE_ORCHESTRATOR_LAMBDA_ARN")
        if not orchestrator_arn:
            raise lambda_execution_error("Orchestrator Lambda ARN not configured")

        payload = {
            "action": "verify_migration",
            "migration_id": migration.id,
        }

        try:
            response = lambda_client.invoke(
                FunctionName=orchestrator_arn,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload)
            )
            result = json.loads(response["Payload"].read())
            
            if result.get("status") != "success" or not result.get("verified"):
                raise lambda_execution_error(f"Migration verification failed: {result.get('error')}")
            
            logger.info("Migration verification successful")
        except ClientError as exc:
            raise lambda_execution_error(f"Failed to invoke verification Lambda: {exc}") from exc
