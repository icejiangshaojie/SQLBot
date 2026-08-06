"""
AI2BI Agent 模型 — Vertical Agent 打包、发布、权限管理

Agent = 业务域 + Skills + 专属表 + 指标 + entry_signals + 隔离规则 + 权限
"""

from sqlmodel import SQLModel, Field, Column
from typing import Optional
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Text, JSON, String, Boolean
import sqlalchemy as sa


class Ai2biAgent(SQLModel, table=True):
    __tablename__ = "ai2bi_agent"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    code: str = Field(sa_column=Column(String(64), unique=True))  # card_agent, corp_fx_agent
    name: str = Field(sa_column=Column(String(128)))  # 卡域分析
    vertical: str = Field(sa_column=Column(String(64)))  # retail_card, corp_fx
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    status: str = Field(default="dev", sa_column=Column(String(32)))  # dev/published/archived
    version: str = Field(default="0.1", sa_column=Column(String(16)))

    # 路由信号（关键词列表 JSON）
    entry_signals: Optional[list] = Field(default=None, sa_column=Column(JSON))

    # 绑定的 Skills（路径列表 JSON）
    skills: Optional[list] = Field(default=None, sa_column=Column(JSON))  # ["card/director/SKILL.md", ...]

    # 专属表（只有这个 Agent 能用）
    exclusive_tables: Optional[list] = Field(default=None, sa_column=Column(JSON))

    # 可引用的基座表（共享）
    shared_tables: Optional[list] = Field(default=None, sa_column=Column(JSON))

    # 绑定指标 ID 列表
    metric_ids: Optional[list] = Field(default=None, sa_column=Column(JSON))

    # 隔离规则
    isolation_rules: Optional[str] = Field(default=None, sa_column=Column(Text))

    # 所属业务线
    business_line: str = Field(default="零售", sa_column=Column(String(32)))

    # 负责人
    owner: Optional[str] = Field(default=None, sa_column=Column(String(128)))

    # 能力边界（新增）
    capabilities: Optional[list] = Field(default=None, sa_column=Column(JSON))
    # ["knowledge_qa", "data_query", "data_analysis"]

    # 分析模板（新增）
    analysis_templates: Optional[list] = Field(default=None, sa_column=Column(JSON))
    # ["trend", "structure_split", "ranking", "anomaly"]

    # 测试集路径（新增）
    test_case_path: Optional[str] = Field(default=None, sa_column=Column(String(256)))

    # 质检配置（新增）
    qa_config: Optional[str] = Field(default=None, sa_column=Column(Text))
    # JSON: {"check_evidence": true, "check_numeric_consistency": true, "block_unsourced_numbers": true}

    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


class Ai2biAgentGrant(SQLModel, table=True):
    """用户对 Agent 的权限"""
    __tablename__ = "ai2bi_agent_grant"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    agent_id: int = Field(sa_column=Column(BigInteger))
    user_id: int = Field(sa_column=Column(BigInteger))
    grant_type: str = Field(default="manual", sa_column=Column(String(32)))  # manual/auto/request
    status: str = Field(default="active", sa_column=Column(String(32)))  # active/revoked
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


class Ai2biAgentRequest(SQLModel, table=True):
    """权限申请"""
    __tablename__ = "ai2bi_agent_request"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    agent_id: int = Field(sa_column=Column(BigInteger))
    user_id: int = Field(sa_column=Column(BigInteger))
    reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    status: str = Field(default="pending", sa_column=Column(String(32)))  # pending/approved/rejected
    reviewer: Optional[str] = Field(default=None, sa_column=Column(String(128)))
    reviewed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))


class Ai2biAgentVersion(SQLModel, table=True):
    """版本历史"""
    __tablename__ = "ai2bi_agent_version"
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    agent_id: int = Field(sa_column=Column(BigInteger))
    version: str = Field(sa_column=Column(String(16)))
    snapshot: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON snapshot
    changelog: Optional[str] = Field(default=None, sa_column=Column(Text))
    published_by: Optional[str] = Field(default=None, sa_column=Column(String(128)))
    published_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
