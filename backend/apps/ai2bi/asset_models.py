"""
AI2BI 数据资产元数据模型

数据来源：知识库 DDL + 手动维护
用途：Agent 上下文、前端展示、SQL 生成辅助

注册到 alembic/env.py 以支持自动迁移。
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import BigInteger, Text, Boolean, DateTime, String, ForeignKey, Integer


# ============================================================================
# 1. 表字典 (Table Dictionary)
# ============================================================================

class Ai2biTableDict(SQLModel, table=True):
    """表字典 — 从 DDL 文件解析或手动维护"""
    __tablename__ = "ai2bi_table_dict"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    domain_code: str = Field(sa_column=Column(String(64), index=True), description="业务域编码: card, corp_fx, corp_deposit...")
    table_name: str = Field(sa_column=Column(String(256), index=True), description="表名, 如 dim_cust_basic_info_ext_d_aiview")
    table_comment: Optional[str] = Field(default=None, sa_column=Column(Text), description="表注释/中文名")
    layer: str = Field(sa_column=Column(String(16)), description="分层: dim, dwd, dws, dm, odm, ads, tmp, other")
    datasource_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger), description="关联的数据源ID")

    # 统计信息
    field_count: int = Field(default=0, sa_column=Column(BigInteger), description="字段数")
    metric_count: int = Field(default=0, sa_column=Column(BigInteger), description="核心指标数")
    dimension_count: int = Field(default=0, sa_column=Column(BigInteger), description="维度数")

    # 上游依赖（从 SQL 血缘分析提取）
    upstream_tables: Optional[str] = Field(default=None, sa_column=Column(Text), description="JSON 数组: ['table1', 'table2']")

    # DDL 原文
    ddl_content: Optional[str] = Field(default=None, sa_column=Column(Text), description="CREATE TABLE 语句原文")

    # 元数据
    is_active: bool = Field(default=True, sa_column=Column(Boolean), description="是否启用")
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


# ============================================================================
# 2. 字段字典 (Field Dictionary)
# ============================================================================

class Ai2biFieldDict(SQLModel, table=True):
    """字段字典 — 从 DDL 解析或手动维护"""
    __tablename__ = "ai2bi_field_dict"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    table_id: int = Field(sa_column=Column(BigInteger, ForeignKey("ai2bi_table_dict.id"), index=True), description="关联表ID")
    domain_code: str = Field(sa_column=Column(String(64), index=True), description="业务域编码")

    # 基本信息
    field_name: str = Field(sa_column=Column(String(128)), description="字段名, 如 cust_no")
    field_type: str = Field(sa_column=Column(String(64)), description="字段类型, 如 STRING, BIGINT, DECIMAL(18,2)")
    field_comment: Optional[str] = Field(default=None, sa_column=Column(Text), description="字段注释/中文名")

    # 业务属性
    category: str = Field(default="other", sa_column=Column(String(32)), description="分类: dimension, metric, filter, partition, other")
    aggregation: Optional[str] = Field(default=None, sa_column=Column(String(32)), description="聚合方式: SUM, AVG, COUNT, MAX, MIN, COUNT_DISTINCT, NONE")

    # 技术属性
    is_partition: bool = Field(default=False, sa_column=Column(Boolean), description="是否是分区字段")
    is_primary_key: bool = Field(default=False, sa_column=Column(Boolean), description="是否是主键")
    is_nullable: bool = Field(default=True, sa_column=Column(Boolean), description="是否可空")

    # 示例值（从采样数据提取）
    sample_values: Optional[str] = Field(default=None, sa_column=Column(Text), description="JSON 数组: ['value1', 'value2']")

    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


# ============================================================================
# 3. 核心指标 (Core Metrics) — 独立字典表
# ============================================================================

class Ai2biMetricDict(SQLModel, table=True):
    """核心指标字典 — 扩展版，支持更完整的指标定义"""
    __tablename__ = "ai2bi_metric_dict"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    domain_code: str = Field(sa_column=Column(String(64), index=True), description="业务域编码")
    metric_number: Optional[str] = Field(default=None, sa_column=Column(String(64)), description="指标编号")

    # 命名
    cn_name: str = Field(sa_column=Column(String(256)), description="中文名")
    en_name: Optional[str] = Field(default=None, sa_column=Column(String(256)), description="英文名")
    alias: Optional[str] = Field(default=None, sa_column=Column(String(256)), description="别名/俗称")

    # 定义
    business_definition: Optional[str] = Field(default=None, sa_column=Column(Text), description="业务定义（人话）")
    calculation: Optional[str] = Field(default=None, sa_column=Column(Text), description="计算公式，如 SUM(trans_amt_hkd)")
    sql_template: Optional[str] = Field(default=None, sa_column=Column(Text), description="SQL 模板")

    # 技术属性
    grain: Optional[str] = Field(default=None, sa_column=Column(String(64)), description="粒度: 日/月/客户/交易")
    time_range: Optional[str] = Field(default=None, sa_column=Column(String(64)), description="默认时间范围")
    unit: Optional[str] = Field(default=None, sa_column=Column(String(32)), description="单位: HKD, 笔, %, 人")

    # 依赖
    source_table_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger), description="主来源表ID")
    source_field: Optional[str] = Field(default=None, sa_column=Column(String(128)), description="来源字段名")
    related_metrics: Optional[str] = Field(default=None, sa_column=Column(Text), description="关联指标 ID 列表 JSON")

    # 状态
    status: str = Field(default="candidate", sa_column=Column(String(32)), description="状态: candidate, confirmed, deprecated")
    version: str = Field(default="1.0", sa_column=Column(String(16)), description="版本号")

    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


# ============================================================================
# 4. 业务规则/注意事项 (Business Rules / Pitfalls)
# ============================================================================

class Ai2biBusinessRule(SQLModel, table=True):
    """业务规则和常见陷阱 — 用于 Agent 参考"""
    __tablename__ = "ai2bi_business_rule"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    domain_code: str = Field(sa_column=Column(String(64), index=True), description="业务域编码")

    # 规则内容
    title: str = Field(sa_column=Column(String(256)), description="规则标题")
    content: str = Field(sa_column=Column(Text), description="规则详细内容")
    category: str = Field(default="general", sa_column=Column(String(32)), description="分类: general, sql, data_quality,口径, pitfall")

    # 关联
    related_table_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, ForeignKey("ai2bi_table_dict.id")), description="关联表")
    related_metric_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, ForeignKey("ai2bi_metric_dict.id")), description="关联指标")

    # 重要性
    severity: str = Field(default="warning", sa_column=Column(String(16)), description="级别: info, warning, critical")

    # 示例
    example: Optional[str] = Field(default=None, sa_column=Column(Text), description="正确示例")
    counter_example: Optional[str] = Field(default=None, sa_column=Column(Text), description="错误示例（反例）")

    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


# ============================================================================
# 5. SQL 模板 (SQL Templates)
# ============================================================================

class Ai2biSqlTemplate(SQLModel, table=True):
    """SQL 取数模板 — 常用查询模式"""
    __tablename__ = "ai2bi_sql_template"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    domain_code: str = Field(sa_column=Column(String(64), index=True), description="业务域编码")

    # 基本信息
    name: str = Field(sa_column=Column(String(256)), description="模板名称")
    description: Optional[str] = Field(default=None, sa_column=Column(Text), description="模板描述")
    scenario: Optional[str] = Field(default=None, sa_column=Column(String(128)), description="适用场景")

    # SQL 内容
    sql_template: str = Field(sa_column=Column(Text), description="SQL 模板，含占位符如 {pt}")
    params: Optional[str] = Field(default=None, sa_column=Column(Text), description="参数说明 JSON")

    # 依赖
    related_table_ids: Optional[str] = Field(default=None, sa_column=Column(Text), description="关联表 ID 列表 JSON")
    related_metric_ids: Optional[str] = Field(default=None, sa_column=Column(Text), description="关联指标 ID 列表 JSON")

    # 统计
    usage_count: int = Field(default=0, sa_column=Column(BigInteger), description="使用次数")

    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


# ============================================================================
# 6. 数据血缘关系 (Data Lineage)
# ============================================================================

class Ai2biTableLineage(SQLModel, table=True):
    """表级血缘关系"""
    __tablename__ = "ai2bi_table_lineage"

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    domain_code: str = Field(sa_column=Column(String(64), index=True), description="业务域编码")
    from_table: str = Field(sa_column=Column(String(256)), description="上游表名")
    to_table: str = Field(sa_column=Column(String(256)), description="下游表名")
    relation_type: str = Field(default="direct", sa_column=Column(String(16)), description="关系类型: direct(直接), indirect(间接)")
    sql_snippet: Optional[str] = Field(default=None, sa_column=Column(Text), description="关联 SQL 片段")

    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
