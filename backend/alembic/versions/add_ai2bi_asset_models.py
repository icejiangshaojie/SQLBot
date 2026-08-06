"""add_ai2bi_asset_models

Revision ID: f8e43d16ae7d
Revises: e6f7a8b9c0d1
Create Date: 2026-08-06 15:26:53.754715

"""
from alembic import op
import sqlalchemy as sa

revision = 'f8e43d16ae7d'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade():
    # 1. ai2bi_table_dict — 表字典
    op.create_table('ai2bi_table_dict',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('domain_code', sa.String(length=64), nullable=True),
        sa.Column('table_name', sa.String(length=256), nullable=True),
        sa.Column('table_comment', sa.Text(), nullable=True),
        sa.Column('layer', sa.String(length=16), nullable=True),
        sa.Column('datasource_id', sa.BigInteger(), nullable=True),
        sa.Column('field_count', sa.BigInteger(), nullable=True),
        sa.Column('metric_count', sa.BigInteger(), nullable=True),
        sa.Column('dimension_count', sa.BigInteger(), nullable=True),
        sa.Column('upstream_tables', sa.Text(), nullable=True),
        sa.Column('ddl_content', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai2bi_table_dict_domain_code', 'ai2bi_table_dict', ['domain_code'])
    op.create_index('ix_ai2bi_table_dict_table_name', 'ai2bi_table_dict', ['table_name'])

    # 2. ai2bi_field_dict — 字段字典
    op.create_table('ai2bi_field_dict',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('table_id', sa.BigInteger(), sa.ForeignKey('ai2bi_table_dict.id'), nullable=True),
        sa.Column('domain_code', sa.String(length=64), nullable=True),
        sa.Column('field_name', sa.String(length=128), nullable=True),
        sa.Column('field_type', sa.String(length=64), nullable=True),
        sa.Column('field_comment', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=32), nullable=True),
        sa.Column('aggregation', sa.String(length=32), nullable=True),
        sa.Column('is_partition', sa.Boolean(), nullable=True),
        sa.Column('is_primary_key', sa.Boolean(), nullable=True),
        sa.Column('is_nullable', sa.Boolean(), nullable=True),
        sa.Column('sample_values', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai2bi_field_dict_domain_code', 'ai2bi_field_dict', ['domain_code'])
    op.create_index('ix_ai2bi_field_dict_table_id', 'ai2bi_field_dict', ['table_id'])

    # 3. ai2bi_metric_dict — 核心指标
    op.create_table('ai2bi_metric_dict',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('domain_code', sa.String(length=64), nullable=True),
        sa.Column('metric_number', sa.String(length=64), nullable=True),
        sa.Column('cn_name', sa.String(length=256), nullable=True),
        sa.Column('en_name', sa.String(length=256), nullable=True),
        sa.Column('alias', sa.String(length=256), nullable=True),
        sa.Column('business_definition', sa.Text(), nullable=True),
        sa.Column('calculation', sa.Text(), nullable=True),
        sa.Column('sql_template', sa.Text(), nullable=True),
        sa.Column('grain', sa.String(length=64), nullable=True),
        sa.Column('time_range', sa.String(length=64), nullable=True),
        sa.Column('unit', sa.String(length=32), nullable=True),
        sa.Column('source_table_id', sa.BigInteger(), nullable=True),
        sa.Column('source_field', sa.String(length=128), nullable=True),
        sa.Column('related_metrics', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('version', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai2bi_metric_dict_domain_code', 'ai2bi_metric_dict', ['domain_code'])

    # 4. ai2bi_business_rule — 业务规则/注意事项
    op.create_table('ai2bi_business_rule',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('domain_code', sa.String(length=64), nullable=True),
        sa.Column('title', sa.String(length=256), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=32), nullable=True),
        sa.Column('related_table_id', sa.BigInteger(), sa.ForeignKey('ai2bi_table_dict.id'), nullable=True),
        sa.Column('related_metric_id', sa.BigInteger(), sa.ForeignKey('ai2bi_metric_dict.id'), nullable=True),
        sa.Column('severity', sa.String(length=16), nullable=True),
        sa.Column('example', sa.Text(), nullable=True),
        sa.Column('counter_example', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai2bi_business_rule_domain_code', 'ai2bi_business_rule', ['domain_code'])

    # 5. ai2bi_sql_template — SQL模板
    op.create_table('ai2bi_sql_template',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('domain_code', sa.String(length=64), nullable=True),
        sa.Column('name', sa.String(length=256), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scenario', sa.String(length=128), nullable=True),
        sa.Column('sql_template', sa.Text(), nullable=True),
        sa.Column('params', sa.Text(), nullable=True),
        sa.Column('related_table_ids', sa.Text(), nullable=True),
        sa.Column('related_metric_ids', sa.Text(), nullable=True),
        sa.Column('usage_count', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai2bi_sql_template_domain_code', 'ai2bi_sql_template', ['domain_code'])

    # 6. ai2bi_table_lineage — 表血缘
    op.create_table('ai2bi_table_lineage',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('domain_code', sa.String(length=64), nullable=True),
        sa.Column('from_table', sa.String(length=256), nullable=True),
        sa.Column('to_table', sa.String(length=256), nullable=True),
        sa.Column('relation_type', sa.String(length=16), nullable=True),
        sa.Column('sql_snippet', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai2bi_table_lineage_domain_code', 'ai2bi_table_lineage', ['domain_code'])


def downgrade():
    op.drop_index('ix_ai2bi_table_lineage_domain_code', table_name='ai2bi_table_lineage')
    op.drop_table('ai2bi_table_lineage')
    op.drop_index('ix_ai2bi_sql_template_domain_code', table_name='ai2bi_sql_template')
    op.drop_table('ai2bi_sql_template')
    op.drop_index('ix_ai2bi_business_rule_domain_code', table_name='ai2bi_business_rule')
    op.drop_table('ai2bi_business_rule')
    op.drop_index('ix_ai2bi_metric_dict_domain_code', table_name='ai2bi_metric_dict')
    op.drop_table('ai2bi_metric_dict')
    op.drop_index('ix_ai2bi_field_dict_table_id', table_name='ai2bi_field_dict')
    op.drop_index('ix_ai2bi_field_dict_domain_code', table_name='ai2bi_field_dict')
    op.drop_table('ai2bi_field_dict')
    op.drop_index('ix_ai2bi_table_dict_table_name', table_name='ai2bi_table_dict')
    op.drop_index('ix_ai2bi_table_dict_domain_code', table_name='ai2bi_table_dict')
    op.drop_table('ai2bi_table_dict')
