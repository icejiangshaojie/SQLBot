"""
AI2BI Phase 0 分析合同 — AnalysisContext / AnalysisFact / AnalysisResult / QA

职责：
1. 定义一次"单查询分析"的稳定契约，供分析引擎、QA、Evidence 持久化和 SSE 共用。
2. 约束数字来源：sql（SQL 直出）/ backend_calc（后端可复现计算）/ model_inferred（模型推导）。
3. 约束终结状态：completed / data_insufficient / blocked / failed / skipped。

设计原则：
- 本模块不访问数据库、不调用 LLM，是可序列化的纯数据合同。
- Phase 0 只支持单结果显示；AnalysisPlan / AnalysisTask / 补充查询见后续阶段。
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    """一次分析的最终状态。阶段状态（started/generating）不在此列，归 SSE 事件。"""
    COMPLETED = "completed"
    DATA_INSUFFICIENT = "data_insufficient"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


class FactSource(str, Enum):
    """数字来源。模型推导在 Phase 0 默认不作为经营结论的唯一证据。"""
    SQL = "sql"
    BACKEND = "backend_calc"
    MODEL = "model_inferred"


class FactStatus(str, Enum):
    VERIFIED = "verified"
    DATA_INSUFFICIENT = "data_insufficient"


class AnalysisFact(BaseModel):
    """一条可定位到 SQL 结果或后端计算的可复现事实。"""
    fact_id: str
    category: str = Field(description="summary/trend/ranking/structure/comparison/anomaly")
    label: str = Field(description="业务可读标签，如 '7 月成功授权消费总额'")
    value: float | None = None
    unit: str | None = None
    source_type: FactSource = FactSource.SQL
    formula: str | None = None
    input_refs: list[str] = Field(default_factory=list, description="引用的 fact_id 或 query 引用")
    row_refs: list[str] = Field(default_factory=list, description="来源行引用，如 row[0]")
    column: str | None = None
    display: str | None = Field(default=None, description="显示值，如 '123.46 万 HKD'")
    status: FactStatus = FactStatus.VERIFIED
    reason: str | None = Field(default=None, description="data_insufficient 时的原因")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class QaFinding(BaseModel):
    """单条 QA 发现。severity: info / warning / block。"""
    code: str
    severity: str = "warning"
    message: str
    fact_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class QaResult(BaseModel):
    """QA 判定。status: passed / warning / blocked。renderable 表示是否允许展示模型正文。"""
    status: str = "passed"
    findings: list[QaFinding] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    renderable: bool = True


class AnalysisContext(BaseModel):
    """一次单查询分析的运行上下文，贯穿 SQL -> Evidence -> Facts -> QA -> 持久化。"""
    record_id: int
    chat_id: int
    source_record_id: int | None = None
    question: str
    datasource_id: int | None = None
    datasource_name: str | None = None
    sql: str
    result: dict[str, Any] = Field(default_factory=dict, description="{fields, data}")
    route_info: dict[str, Any] = Field(default_factory=dict)
    metric_context: list[dict[str, Any]] = Field(default_factory=list)
    template: dict[str, Any] = Field(default_factory=dict)
    qa_config: dict[str, Any] = Field(default_factory=dict)
    agent_code: str | None = None
    agent_name: str | None = None
    started_at: str | None = None


class AnalysisResult(BaseModel):
    """一次分析的最终结果，用于持久化与 SSE。"""
    status: AnalysisStatus
    facts: list[AnalysisFact] = Field(default_factory=list)
    final_text: str | None = None
    qa: QaResult | None = None
    error: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ═══ Q3 专题分析合同 ═══════════════════════════════════════════

class AnalysisContract(BaseModel):
    """Q3 用户本次专题分析的已确认口径。"""
    question: str
    intent_type: str = "topic_analysis"
    agent_ref: str | None = None
    topic_template: str | None = None
    metrics: list[str] = Field(default_factory=list)
    time_range: dict[str, Any] = Field(default_factory=dict)
    population: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    mandatory_filters: list[str] = Field(default_factory=list)
    comparison_baseline: str | None = None
    status: str = "inferred"  # inferred | needs_confirmation | confirmed


class PlanQuery(BaseModel):
    """一条计划查询。"""
    query_id: str
    purpose: str
    required: bool = False
    status: str = "pending"  # pending | running | completed | failed | data_insufficient
    sql: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    result_hash: str | None = None
    row_count: int = 0
    facts: list[AnalysisFact] = Field(default_factory=list)
    error: str | None = None


class AnalysisPlan(BaseModel):
    """Q3 专题分析计划：受控多查询。"""
    plan_id: str
    mode: str = "topic_analysis"
    max_queries: int = 3
    queries: list[PlanQuery] = Field(default_factory=list)
    operators: list[str] = Field(default_factory=list)
    limits: dict[str, Any] = Field(default_factory=dict)


class BpFinding(BaseModel):
    """Q3 BP Agent 的一条发现。"""
    category: str = "general"  # summary/trend/structure/comparison/anomaly/limitation
    text: str
    fact_ids: list[str] = Field(default_factory=list)
    query_ids: list[str] = Field(default_factory=list)


class BpOutput(BaseModel):
    """Q3 BP Agent 的结构化输出。"""
    executive_summary: list[BpFinding] = Field(default_factory=list)
    findings: list[BpFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    markdown: str | None = None


class TopicAnalysisResult(BaseModel):
    """Q3 专题分析最终结果。"""
    status: AnalysisStatus
    contract: AnalysisContract | None = None
    plan: AnalysisPlan | None = None
    facts: list[AnalysisFact] = Field(default_factory=list)
    bp_output: BpOutput | None = None
    qa: QaResult | None = None
    error: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
