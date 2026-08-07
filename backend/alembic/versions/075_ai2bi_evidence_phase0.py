"""extend ai2bi_evidence for phase0 analysis

Revision ID: a1b2c3d4e5f6
Revises: f8e43d16ae7d
Create Date: 2026-08-07
"""
from alembic import op
import sqlalchemy as sa


revision = 'f9e0d1c2b3a4'
down_revision = 'f8e43d16ae7d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('ai2bi_evidence', sa.Column('source_record_id', sa.BigInteger(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('analysis_status', sa.String(length=32), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('analysis_error', sa.Text(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('analysis_facts', sa.Text(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('qa_result', sa.Text(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('analysis_output', sa.Text(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('result_hash', sa.String(length=64), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('metric_context', sa.Text(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('agent_snapshot', sa.Text(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('model_name', sa.String(length=128), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('total_tokens', sa.BigInteger(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('duration_ms', sa.BigInteger(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.create_index('ix_ai2bi_evidence_source_record_id', 'ai2bi_evidence', ['source_record_id'])


def downgrade() -> None:
    op.drop_index('ix_ai2bi_evidence_source_record_id', table_name='ai2bi_evidence')
    op.drop_column('ai2bi_evidence', 'updated_at')
    op.drop_column('ai2bi_evidence', 'duration_ms')
    op.drop_column('ai2bi_evidence', 'total_tokens')
    op.drop_column('ai2bi_evidence', 'model_name')
    op.drop_column('ai2bi_evidence', 'agent_snapshot')
    op.drop_column('ai2bi_evidence', 'metric_context')
    op.drop_column('ai2bi_evidence', 'result_hash')
    op.drop_column('ai2bi_evidence', 'analysis_output')
    op.drop_column('ai2bi_evidence', 'qa_result')
    op.drop_column('ai2bi_evidence', 'analysis_facts')
    op.drop_column('ai2bi_evidence', 'analysis_error')
    op.drop_column('ai2bi_evidence', 'analysis_status')
    op.drop_column('ai2bi_evidence', 'source_record_id')