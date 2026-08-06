"""
AI2BI Test Case 模型 — 回归测试用例和运行记录
"""

from sqlmodel import SQLModel, Field, Column
from typing import Optional
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Text, String
import sqlalchemy as sa


class Ai2biTestCase(SQLModel, table=True):
    """回归测试用例"""
    __tablename__ = "ai2bi_test_case"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    agent_id: int = Field(sa_column=Column(BigInteger))
    test_type: str = Field(sa_column=Column(String(32)))   # routing / sql_regression / evidence
    question: str = Field(sa_column=Column(Text))
    expected_agent: Optional[str] = Field(default=None, sa_column=Column(String(128)))
    expected_tables: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON list
    expected_sql_pattern: Optional[str] = Field(default=None, sa_column=Column(Text))
    expected_evidence_count: int = Field(default=0)
    last_run_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    last_passed: Optional[bool] = Field(default=None)
    last_result: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON

    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


class Ai2biTestRun(SQLModel, table=True):
    """测试运行记录"""
    __tablename__ = "ai2bi_test_run"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    agent_id: int = Field(sa_column=Column(BigInteger))
    total: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    details: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    run_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
