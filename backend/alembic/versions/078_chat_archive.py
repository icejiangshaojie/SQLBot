"""add is_archived to chat for conversation archiving

Revision ID: a1b2c3d4e5f6
Revises: q3topic0001
Create Date: 2026-08-07
"""
from alembic import op
import sqlalchemy as sa

revision = 'chatarchive0001'
down_revision = 'q3topic0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'chat',
        sa.Column('is_archived', sa.Boolean(), nullable=True, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('chat', 'is_archived')