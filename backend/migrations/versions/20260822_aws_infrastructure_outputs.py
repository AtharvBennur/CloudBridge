"""Persist CloudFormation Lambda outputs for each customer AWS connection."""
from alembic import op
import sqlalchemy as sa

revision = "20260822_aws_infra_outputs"
down_revision = "20260822_lambda_request_id"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("aws_connections", sa.Column("cloudformation_stack_name", sa.String(255), nullable=False, server_default="CloudBridgecf"))
    op.add_column("aws_connections", sa.Column("orchestrator_lambda_arn", sa.String(512)))
    op.add_column("aws_connections", sa.Column("worker_lambda_arn", sa.String(512)))
    op.add_column("aws_connections", sa.Column("validation_lambda_arn", sa.String(512)))
    op.add_column("aws_connections", sa.Column("dynamodb_table_name", sa.String(255)))
    op.add_column("aws_connections", sa.Column("infrastructure_discovered_at", sa.DateTime()))
    op.add_column("aws_connections", sa.Column("infrastructure_last_verified_at", sa.DateTime()))

def downgrade():
    for column in ("infrastructure_last_verified_at", "infrastructure_discovered_at", "dynamodb_table_name", "validation_lambda_arn", "worker_lambda_arn", "orchestrator_lambda_arn", "cloudformation_stack_name"):
        op.drop_column("aws_connections", column)
