"""create ai2bi test case tables

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai2bi_test_case',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('agent_id', sa.BigInteger(), nullable=False),
        sa.Column('test_type', sa.String(32), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('expected_agent', sa.String(128), nullable=True),
        sa.Column('expected_tables', sa.Text(), nullable=True),
        sa.Column('expected_sql_pattern', sa.Text(), nullable=True),
        sa.Column('expected_evidence_count', sa.Integer(), server_default='0'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_passed', sa.Boolean(), nullable=True),
        sa.Column('last_result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'ai2bi_test_run',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('agent_id', sa.BigInteger(), nullable=False),
        sa.Column('total', sa.Integer(), server_default='0'),
        sa.Column('passed', sa.Integer(), server_default='0'),
        sa.Column('failed', sa.Integer(), server_default='0'),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('run_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('ai2bi_test_run')
    op.drop_table('ai2bi_test_case')
