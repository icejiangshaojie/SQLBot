"""
AI2BI Q3 专题分析编排器 — 多查询执行、结果收集、确定性 Facts。

职责：
1. 按 AnalysisPlan 顺序执行计划查询（必需/可选）。
2. 收集每个查询的结果、行数、结果 hash。
3. 对每个结果集运行确定性分析引擎，产出 Facts。
4. 组装多个查询的 Evidence Pack。

设计原则：
- 纯编排，不直接访问数据库；SQL 生成与执行通过注入的回调完成。
- 必需查询失败 -> 整体失败；可选查询失败 -> 降级并保留已有结果。
- 每个查询保留 result_ref，Facts 通过 query_refs 追溯来源。
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable

from .analysis_contract import (
    AnalysisFact,
    AnalysisPlan,
    AnalysisStatus,
    PlanQuery,
    TopicAnalysisResult,
)
from .analysis_engine import analyze_result

# SQL 生成回调：给定问题+上下文+用途，返回 SQL 文本
SqlGenerator = Callable[[str, str, str], str]
# SQL 执行回调：给定 SQL，返回 {fields, data}
SqlExecutor = Callable[[str], dict[str, Any]]


def run_topic_plan(
    plan: AnalysisPlan,
    question: str,
    context_prompt: str,
    sql_generator: SqlGenerator,
    sql_executor: SqlExecutor,
    metric_context: list | None = None,
) -> TopicAnalysisResult:
    """执行专题分析计划，返回 TopicAnalysisResult。

    Args:
        plan: 待执行的计划。
        question: 用户问题。
        context_prompt: 路由上下文（Agent/Skill/表/指标）。
        sql_generator: 生成单条查询 SQL 的回调 (question, context, purpose) -> sql。
        sql_executor: 执行 SQL 的回调 (sql) -> {fields, data}。
        metric_context: 指标上下文快照。
    """
    all_facts: list[AnalysisFact] = []
    required_failed = False

    for pq in plan.queries:
        pq.status = "running"
        try:
            sql = sql_generator(question, context_prompt, pq.purpose)
            if not sql or not sql.strip():
                pq.status = "data_insufficient"
                pq.error = "未能生成该查询的 SQL"
                if pq.required:
                    required_failed = True
                continue

            pq.sql = sql
            result = sql_executor(sql)
            pq.result = result
            pq.row_count = len(result.get("data") or [])

            # 结果 hash
            pq.result_hash = _result_hash(result)

            # 确定性 Facts
            facts = analyze_result(result, metric_context)
            pq.facts = facts
            all_facts.extend(facts)

            if not result.get("data"):
                pq.status = "data_insufficient"
                if pq.required:
                    # 必需查询空结果 -> 整体数据不足
                    return TopicAnalysisResult(
                        status=AnalysisStatus.DATA_INSUFFICIENT,
                        contract=None,
                        plan=plan,
                        facts=all_facts,
                        reason=f"必需查询 '{pq.query_id}' 无数据返回，无法完成专题分析。",
                    )
            else:
                pq.status = "completed"
        except Exception as e:
            pq.status = "failed"
            pq.error = str(e)
            if pq.required:
                required_failed = True

    if required_failed:
        return TopicAnalysisResult(
            status=AnalysisStatus.FAILED,
            contract=None,
            plan=plan,
            facts=all_facts,
            error="存在必需查询执行失败，专题分析终止。",
        )

    # 没有完成任何查询（全是可选失败/数据不足）
    completed = [q for q in plan.queries if q.status == "completed"]
    if not completed and not all_facts:
        return TopicAnalysisResult(
            status=AnalysisStatus.DATA_INSUFFICIENT,
            contract=None,
            plan=plan,
            facts=all_facts,
            reason="所有计划查询均未返回可用数据。",
        )

    return TopicAnalysisResult(
        status=AnalysisStatus.COMPLETED,
        contract=None,
        plan=plan,
        facts=all_facts,
        metadata={"completed_queries": len(completed), "total_queries": len(plan.queries)},
    )


def _result_hash(result: dict) -> str:
    import json
    return hashlib.sha256(
        json.dumps(result, default=str, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:32]