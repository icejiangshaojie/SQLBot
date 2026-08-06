"""
AI2BI Evidence 模型 — 每次回答的证据链记录

记录一次问答中：
- 路由信息（命中哪个 Agent、置信度、是否兜底）
- SQL 证据（执行的 SQL、行数、结果摘要）
- 证据来源标注（SQL 直出 / 后端计算 / 模型推导）
- 质检结果（是否通过、违规列表）
"""

from sqlmodel import SQLModel, Field, Column
from typing import Optional
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Text, Boolean
import sqlalchemy as sa


class Ai2biEvidence(SQLModel, table=True):
    """每次回答的证据链记录"""
    __tablename__ = "ai2bi_evidence"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    record_id: int = Field(sa_column=Column(BigInteger))          # 关联 chat_record
    chat_id: int = Field(sa_column=Column(BigInteger))
    agent_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))

    # 路由信息 JSON: {agent_code, agent_name, sub_skill, confidence, is_fallback}
    route_info: Optional[str] = Field(default=None, sa_column=Column(Text))

    # SQL 证据
    sql_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    sql_executed: bool = Field(default=False, sa_column=Column(Boolean))
    sql_row_count: int = Field(default=0)
    # JSON: {columns, row_count, sample_rows, partition_info}
    sql_result_summary: Optional[str] = Field(default=None, sa_column=Column(Text))

    # 证据来源标注
    # JSON list: [{"value": 1234567, "source": "sql", "column": "trans_amt_hkd", "row_index": 0}]
    sourced_numbers: Optional[str] = Field(default=None, sa_column=Column(Text))
    # JSON list: [{"value": "12.3%", "source": "backend_calc", "formula": "a/b", "inputs": [...]}]
    derived_numbers: Optional[str] = Field(default=None, sa_column=Column(Text))
    # JSON list: [{"value": "约5000", "claim": "模型估算", "warning": "无SQL依据"}]
    model_inferred: Optional[str] = Field(default=None, sa_column=Column(Text))

    # 质检结果
    qa_passed: Optional[bool] = Field(default=None, sa_column=Column(Boolean))
    # JSON list: ["数值1234无SQL依据", "路由未命中Agent"]
    qa_violations: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
