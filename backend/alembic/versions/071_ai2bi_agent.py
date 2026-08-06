"""create ai2bi agent tables

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai2bi_agent',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(64), unique=True),
        sa.Column('name', sa.String(128)),
        sa.Column('vertical', sa.String(64)),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.String(32), server_default='dev'),
        sa.Column('version', sa.String(16), server_default='0.1'),
        sa.Column('entry_signals', sa.JSON()),
        sa.Column('skills', sa.JSON()),
        sa.Column('exclusive_tables', sa.JSON()),
        sa.Column('shared_tables', sa.JSON()),
        sa.Column('metric_ids', sa.JSON()),
        sa.Column('isolation_rules', sa.Text()),
        sa.Column('business_line', sa.String(32), server_default='零售'),
        sa.Column('owner', sa.String(128)),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_table(
        'ai2bi_agent_grant',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('agent_id', sa.BigInteger()),
        sa.Column('user_id', sa.BigInteger()),
        sa.Column('grant_type', sa.String(32), server_default='manual'),
        sa.Column('status', sa.String(32), server_default='active'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_table(
        'ai2bi_agent_request',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('agent_id', sa.BigInteger()),
        sa.Column('user_id', sa.BigInteger()),
        sa.Column('reason', sa.Text()),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('reviewer', sa.String(128)),
        sa.Column('reviewed_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_table(
        'ai2bi_agent_version',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('agent_id', sa.BigInteger()),
        sa.Column('version', sa.String(16)),
        sa.Column('snapshot', sa.Text()),
        sa.Column('changelog', sa.Text()),
        sa.Column('published_by', sa.String(128)),
        sa.Column('published_at', sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table('ai2bi_agent_version')
    op.drop_table('ai2bi_agent_request')
    op.drop_table('ai2bi_agent_grant')
    op.drop_table('ai2bi_agent')
