# AI2BI module models: metrics, memory
# These models are registered in alembic/env.py for migration autogenerate.

from sqlmodel import SQLModel, Field, Column
from typing import Optional
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Text, JSON, String
import sqlalchemy as sa

# ─── 指标管理 ─────────────────────────────────────

class Ai2biMetricDomain(SQLModel, table=True):
    __tablename__ = "ai2bi_metric_domain"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    code: str = Field(sa_column=Column(String(64), unique=True))
    cn_name: str = Field(sa_column=Column(String(128)))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    owner: Optional[str] = Field(default=None, sa_column=Column(String(128)))
    sort_order: int = Field(default=0)


class Ai2biMetric(SQLModel, table=True):
    __tablename__ = "ai2bi_metric"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    domain_id: int = Field(sa_column=Column(BigInteger))
    metric_number: Optional[str] = Field(default=None, sa_column=Column(String(64)))
    cn_name: str = Field(sa_column=Column(String(256)))
    en_name: Optional[str] = Field(default=None, sa_column=Column(String(256)))
    tier: str = Field(default="L2", sa_column=Column(String(8)))  # L1/L2/L3
    business_definition: Optional[str] = Field(default=None, sa_column=Column(Text))
    calculation: Optional[str] = Field(default=None, sa_column=Column(Text))
    mandatory_rules: Optional[str] = Field(default=None, sa_column=Column(Text))
    sql_template: Optional[str] = Field(default=None, sa_column=Column(Text))
    dimensions: Optional[list] = Field(default=None, sa_column=Column(JSON))
    grain: Optional[str] = Field(default=None, sa_column=Column(String(128)))
    source_tables: Optional[str] = Field(default=None, sa_column=Column(Text))
    owner: Optional[str] = Field(default=None, sa_column=Column(String(128)))
    status: str = Field(default="candidate", sa_column=Column(String(32)))
    version: int = Field(default=1)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


class Ai2biMetricHistory(SQLModel, table=True):
    __tablename__ = "ai2bi_metric_history"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    metric_id: int = Field(sa_column=Column(BigInteger))
    version: int = Field(default=1)
    snapshot: Optional[str] = Field(default=None, sa_column=Column(Text))
    change_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    changed_by: Optional[str] = Field(default=None, sa_column=Column(String(128)))
    changed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


# ─── 我的记忆 ─────────────────────────────────────

class Ai2biMemory(SQLModel, table=True):
    __tablename__ = "ai2bi_memory"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    user_id: int = Field(sa_column=Column(BigInteger))
    scope: str = Field(default="user", sa_column=Column(String(32)))  # user/project/session/feedback
    category: Optional[str] = Field(default=None, sa_column=Column(String(128)))
    content: str = Field(sa_column=Column(Text))
    source_chat_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    source_record_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    confidence: float = Field(default=0.5)
    pinned: bool = Field(default=False)
    status: str = Field(default="active", sa_column=Column(String(32)))
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


class Ai2biMemorySummary(SQLModel, table=True):
    __tablename__ = "ai2bi_memory_summary"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    user_id: int = Field(sa_column=Column(BigInteger))
    scope: str = Field(default="session", sa_column=Column(String(32)))
    title: Optional[str] = Field(default=None, sa_column=Column(String(256)))
    summary: str = Field(sa_column=Column(Text))
    period_start: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    period_end: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
