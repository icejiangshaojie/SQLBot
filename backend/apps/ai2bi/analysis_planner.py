"""
AI2BI Q3 专题分析计划器 — 从意图与专题模板生成 AnalysisContract 和 AnalysisPlan。

职责：
1. 从用户问题 + 模板匹配生成 AnalysisContract（口径）。
2. 基于模板的查询清单生成 AnalysisPlan（受控多查询）。
3. 口径不明确时返回 needs_confirmation，不执行查询。

设计原则：
- 纯函数，不访问数据库、不调用 LLM。
- 计划查询只有用途，不含具体 SQL（SQL 由下游生成器产出）。
"""

from __future__ import annotations

import uuid
from typing import Any

from .analysis_contract import AnalysisContract, AnalysisPlan, PlanQuery
from .topic_templates import get_topic_template, match_topic_template


def build_topic_contract(question: str) -> AnalysisContract:
    """生成专题分析口径。自动匹配模板，口径取自模板定义。"""
    template_id, tpl = match_topic_template(question)
    if not template_id or not tpl:
        return AnalysisContract(
            question=question,
            intent_type="analysis",
            status="needs_confirmation",
        )
    return AnalysisContract(
        question=question,
        intent_type="topic_analysis",
        topic_template=template_id,
        metrics=list(tpl.get("metrics", [])),
        dimensions=list(tpl.get("dimensions", [])),
        mandatory_filters=list(tpl.get("mandatory_filters", [])),
        comparison_baseline="活动前同期或上月" if template_id == "campaign_effect_review" else None,
        status="confirmed",
    )


def build_topic_plan(question: str, max_queries: int = 3) -> AnalysisPlan:
    """生成专题分析计划。无匹配模板时返回空计划。"""
    template_id, tpl = match_topic_template(question)
    if not template_id or not tpl:
        return AnalysisPlan(plan_id=_new_plan_id(), mode="topic_analysis", max_queries=max_queries)

    queries = []
    for q in tpl.get("queries", []):
        queries.append(PlanQuery(
            query_id=q["query_id"],
            purpose=q["purpose"],
            required=q.get("required", False),
        ))

    limits = dict(tpl.get("limits", {}))
    limits["max_queries"] = max_queries

    return AnalysisPlan(
        plan_id=_new_plan_id(),
        mode="topic_analysis",
        max_queries=max_queries,
        queries=queries,
        operators=list(tpl.get("operators", [])),
        limits=limits,
    )


def _new_plan_id() -> str:
    return f"plan_{uuid.uuid4().hex[:12]}"


def confirm_contract(contract: AnalysisContract) -> AnalysisContract:
    """口径已确认，标记为 confirmed。"""
    contract.status = "confirmed"
    return contract