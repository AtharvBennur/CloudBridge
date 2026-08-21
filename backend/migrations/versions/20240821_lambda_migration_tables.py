"""Add Lambda migration tracking tables

Revision ID: lambda_migration
Revises: 
Create Date: 2024-08-21

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'lambda_migration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create lambda_migrations table
    op.create_table(
        'lambda_migrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('migration_id', sa.Integer(), nullable=False),
        sa.Column('aws_connection_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'cancelled', name='lambdamigrationstatus'), nullable=False),
        sa.Column('orchestrator_arn', sa.String(length=255), nullable=True),
        sa.Column('worker_arn', sa.String(length=255), nullable=True),
        sa.Column('chunks_created', sa.Integer(), nullable=False, default=0),
        sa.Column('chunks_completed', sa.Integer(), nullable=False, default=0),
        sa.Column('chunks_failed', sa.Integer(), nullable=False, default=0),
        sa.Column('chunks_total', sa.Integer(), nullable=False, default=0),
        sa.Column('rows_migrated', sa.BigInteger(), nullable=False, default=0),
        sa.Column('rows_total', sa.BigInteger(), nullable=False, default=0),
        sa.Column('progress_percent', sa.Float(), nullable=False, default=0.0),
        sa.Column('current_stage', sa.String(length=100), nullable=True, default='initializing'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['migration_id'], ['migration_jobs.id'], ),
        sa.ForeignKeyConstraint(['aws_connection_id'], ['aws_connections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create lambda_chunks table
    op.create_table(
        'lambda_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lambda_migration_id', sa.Integer(), nullable=False),
        sa.Column('chunk_id', sa.String(length=255), nullable=False),
        sa.Column('table_name', sa.String(length=255), nullable=False),
        sa.Column('start_row', sa.BigInteger(), nullable=False, default=0),
        sa.Column('end_row', sa.BigInteger(), nullable=False, default=0),
        sa.Column('estimated_rows', sa.BigInteger(), nullable=False, default=0),
        sa.Column('status', sa.String(length=50), nullable=True, default='PENDING'),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('rows_migrated', sa.BigInteger(), nullable=False, default=0),
        sa.Column('rows_failed', sa.BigInteger(), nullable=False, default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('lambda_request_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['lambda_migration_id'], ['lambda_migrations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chunk_id')
    )
    
    # Create indexes
    op.create_index('ix_lambda_migrations_migration_id', 'lambda_migrations', ['migration_id'])
    op.create_index('ix_lambda_migrations_status', 'lambda_migrations', ['status'])
    op.create_index('ix_lambda_chunks_lambda_migration_id', 'lambda_chunks', ['lambda_migration_id'])
    op.create_index('ix_lambda_chunks_status', 'lambda_chunks', ['status'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_lambda_chunks_status', table_name='lambda_chunks')
    op.drop_index('ix_lambda_chunks_lambda_migration_id', table_name='lambda_chunks')
    op.drop_index('ix_lambda_migrations_status', table_name='lambda_migrations')
    op.drop_index('ix_lambda_migrations_migration_id', table_name='lambda_migrations')
    
    # Drop tables
    op.drop_table('lambda_chunks')
    op.drop_table('lambda_migrations')
