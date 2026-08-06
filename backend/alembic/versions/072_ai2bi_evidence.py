"""create ai2bi evidence table

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai2bi_evidence',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('record_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('agent_id', sa.BigInteger(), nullable=True),
        sa.Column('route_info', sa.Text(), nullable=True),
        sa.Column('sql_text', sa.Text(), nullable=True),
        sa.Column('sql_executed', sa.Boolean(), server_default='false'),
        sa.Column('sql_row_count', sa.Integer(), server_default='0'),
        sa.Column('sql_result_summary', sa.Text(), nullable=True),
        sa.Column('sourced_numbers', sa.Text(), nullable=True),
        sa.Column('derived_numbers', sa.Text(), nullable=True),
        sa.Column('model_inferred', sa.Text(), nullable=True),
        sa.Column('qa_passed', sa.Boolean(), nullable=True),
        sa.Column('qa_violations', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_ai2bi_evidence_record_id', 'ai2bi_evidence', ['record_id'])
    op.create_index('ix_ai2bi_evidence_chat_id', 'ai2bi_evidence', ['chat_id'])


def downgrade() -> None:
    op.drop_index('ix_ai2bi_evidence_chat_id', table_name='ai2bi_evidence')
    op.drop_index('ix_ai2bi_evidence_record_id', table_name='ai2bi_evidence')
    op.drop_table('ai2bi_evidence')
