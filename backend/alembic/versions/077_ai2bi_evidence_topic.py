"""add Q3 topic analysis fields to ai2bi_evidence

Revision ID: q3topic0001
Revises: q2intent0001
Create Date: 2026-08-07
"""
from alembic import op
import sqlalchemy as sa


revision = 'q3topic0001'
down_revision = 'q2intent0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('ai2bi_evidence', sa.Column('topic_contract', sa.Text(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('topic_plan', sa.Text(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('topic_bp_output', sa.Text(), nullable=True))
    op.add_column('ai2bi_evidence', sa.Column('topic_queries', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('ai2bi_evidence', 'topic_queries')
    op.drop_column('ai2bi_evidence', 'topic_bp_output')
    op.drop_column('ai2bi_evidence', 'topic_plan')
    op.drop_column('ai2bi_evidence', 'topic_contract')