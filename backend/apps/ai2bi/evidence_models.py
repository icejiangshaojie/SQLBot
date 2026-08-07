"""
AI2BI Evidence 模型 — 每次回答的证据链记录

记录一次问答中：
- 路由信息（命中哪个 Agent、置信度、是否兜底）
- SQL 证据（执行的 SQL、行数、结果摘要）
- 分析状态（completed / data_insufficient / blocked / failed / skipped）
- 确定性分析 Facts（sql / backend_calc / model_inferred）
- 质检结果（status / findings）
- 分析文本与运行元数据
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text
from sqlmodel import Column, Field, SQLModel


class Ai2biEvidence(SQLModel, table=True):
    """每次回答的证据链记录"""
    __tablename__ = "ai2bi_evidence"
    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    record_id: int = Field(sa_column=Column(BigInteger))          # 关联 chat_record（分析记录）
    chat_id: int = Field(sa_column=Column(BigInteger))
    agent_id: int | None = Field(default=None, sa_column=Column(BigInteger))
    source_record_id: int | None = Field(default=None, sa_column=Column(BigInteger))  # 原始取数记录

    # 路由信息 JSON: {agent_code, agent_name, sub_skill, confidence, is_fallback}
    route_info: str | None = Field(default=None, sa_column=Column(Text))

    # SQL 证据
    sql_text: str | None = Field(default=None, sa_column=Column(Text))
    sql_executed: bool = Field(default=False, sa_column=Column(Boolean))
    sql_row_count: int = Field(default=0)
    # JSON: {columns, row_count, sample_rows, partition_info}
    sql_result_summary: str | None = Field(default=None, sa_column=Column(Text))

    # 证据来源标注
    # JSON list: [{"value": 1234567, "source": "sql", "column": "trans_amt_hkd", "row_index": 0}]
    sourced_numbers: str | None = Field(default=None, sa_column=Column(Text))
    # JSON list: [{"value": "12.3%", "source": "backend_calc", "formula": "a/b", "inputs": [...]}]
    derived_numbers: str | None = Field(default=None, sa_column=Column(Text))
    # JSON list: [{"value": "约5000", "claim": "模型估算", "warning": "无SQL依据"}]
    model_inferred: str | None = Field(default=None, sa_column=Column(Text))

    # 分析状态与结果
    analysis_status: str | None = Field(default=None, sa_column=Column(String(32)))
    analysis_error: str | None = Field(default=None, sa_column=Column(Text))
    # JSON list: AnalysisFact[]（确定性分析事实）
    analysis_facts: str | None = Field(default=None, sa_column=Column(Text))
    # JSON: QaResult
    qa_result: str | None = Field(default=None, sa_column=Column(Text))
    # 完整分析输出文本
    analysis_output: str | None = Field(default=None, sa_column=Column(Text))

    # 运行元数据
    result_hash: str | None = Field(default=None, sa_column=Column(String(64)))
    metric_context: str | None = Field(default=None, sa_column=Column(Text))
    agent_snapshot: str | None = Field(default=None, sa_column=Column(Text))
    model_name: str | None = Field(default=None, sa_column=Column(String(128)))
    total_tokens: int | None = Field(default=None, sa_column=Column(BigInteger))
    duration_ms: int | None = Field(default=None, sa_column=Column(BigInteger))

    # 质检结果（兼容旧字段）
    qa_passed: bool | None = Field(default=None, sa_column=Column(Boolean))
    # JSON list: ["数值1234无SQL依据", ...]
    qa_violations: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime | None = Field(default=None, sa_column=Column(DateTime))
    updated_at: datetime | None = Field(default=None, sa_column=Column(DateTime))
