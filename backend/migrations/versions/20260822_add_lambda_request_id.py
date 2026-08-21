"""Persist the AWS request ID returned by the accepted Lambda invocation."""

from alembic import op
import sqlalchemy as sa

revision = "20260822_lambda_request_id"
down_revision = "lambda_migration"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lambda_migrations", sa.Column("orchestrator_request_id", sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column("lambda_migrations", "orchestrator_request_id")
