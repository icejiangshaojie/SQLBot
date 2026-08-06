"""add agent capabilities fields

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('ai2bi_agent', sa.Column('capabilities', sa.JSON(), nullable=True))
    op.add_column('ai2bi_agent', sa.Column('analysis_templates', sa.JSON(), nullable=True))
    op.add_column('ai2bi_agent', sa.Column('test_case_path', sa.String(256), nullable=True))
    op.add_column('ai2bi_agent', sa.Column('qa_config', sa.Text(), nullable=True))

    # Set default capabilities for existing agents
    op.execute("""
        UPDATE ai2bi_agent
        SET capabilities = '["knowledge_qa", "data_query", "data_analysis"]'::jsonb
        WHERE capabilities IS NULL
    """)


def downgrade() -> None:
    op.drop_column('ai2bi_agent', 'qa_config')
    op.drop_column('ai2bi_agent', 'test_case_path')
    op.drop_column('ai2bi_agent', 'analysis_templates')
    op.drop_column('ai2bi_agent', 'capabilities')
