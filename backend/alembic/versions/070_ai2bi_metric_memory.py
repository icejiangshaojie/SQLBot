"""create ai2bi metric and memory tables

Revision ID: a2b3c4d5e6f7
Revises: 1f82cad3546e
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'a2b3c4d5e6f7'
down_revision = '1f82cad3546e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai2bi_metric_domain',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(64), unique=True),
        sa.Column('cn_name', sa.String(128)),
        sa.Column('description', sa.Text()),
        sa.Column('owner', sa.String(128)),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
    )

    op.create_table(
        'ai2bi_metric',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('domain_id', sa.BigInteger()),
        sa.Column('metric_number', sa.String(64)),
        sa.Column('cn_name', sa.String(256)),
        sa.Column('en_name', sa.String(256)),
        sa.Column('tier', sa.String(8), server_default='L2'),
        sa.Column('business_definition', sa.Text()),
        sa.Column('calculation', sa.Text()),
        sa.Column('mandatory_rules', sa.Text()),
        sa.Column('sql_template', sa.Text()),
        sa.Column('dimensions', sa.JSON()),
        sa.Column('grain', sa.String(128)),
        sa.Column('source_tables', sa.Text()),
        sa.Column('owner', sa.String(128)),
        sa.Column('status', sa.String(32), server_default='candidate'),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table(
        'ai2bi_metric_history',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('metric_id', sa.BigInteger()),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('snapshot', sa.Text()),
        sa.Column('change_reason', sa.Text()),
        sa.Column('changed_by', sa.String(128)),
        sa.Column('changed_at', sa.DateTime()),
    )

    op.create_table(
        'ai2bi_memory',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger()),
        sa.Column('scope', sa.String(32), server_default='user'),
        sa.Column('category', sa.String(128)),
        sa.Column('content', sa.Text()),
        sa.Column('source_chat_id', sa.BigInteger()),
        sa.Column('source_record_id', sa.BigInteger()),
        sa.Column('confidence', sa.Float(), server_default='0.5'),
        sa.Column('pinned', sa.Boolean(), server_default='false'),
        sa.Column('status', sa.String(32), server_default='active'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table(
        'ai2bi_memory_summary',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger()),
        sa.Column('scope', sa.String(32), server_default='session'),
        sa.Column('title', sa.String(256)),
        sa.Column('summary', sa.Text()),
        sa.Column('period_start', sa.DateTime()),
        sa.Column('period_end', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table('ai2bi_memory_summary')
    op.drop_table('ai2bi_memory')
    op.drop_table('ai2bi_metric_history')
    op.drop_table('ai2bi_metric')
    op.drop_table('ai2bi_metric_domain')
