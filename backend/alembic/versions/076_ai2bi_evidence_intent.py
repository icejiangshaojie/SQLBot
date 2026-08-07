"""add analysis_intent to ai2bi_evidence for Q2 intent gating

Revision ID: q2intent0001
Revises: f9e0d1c2b3a4
Create Date: 2026-08-07
"""
from alembic import op
import sqlalchemy as sa


revision = 'q2intent0001'
down_revision = 'f9e0d1c2b3a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('ai2bi_evidence', sa.Column('analysis_intent', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('ai2bi_evidence', 'analysis_intent')