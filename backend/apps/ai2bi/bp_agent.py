"""
AI2BI Q3 数据分析 BP Agent — 从确定性 Facts 归纳业务发现。

职责：
1. 从 Facts 按类别归纳业务发现（趋势/结构/排名/对比/异常）。
2. 每个发现标注引用的 fact_ids。
3. 对缺失数据提出限制说明和下一步问题。

设计原则：
- BP Agent 不取数、不编造事实，只归纳已有 Facts。
- 每个发现必须关联 fact_id；无事实支撑的内容进 limitations 而非 findings。
- 输出结构化 BpOutput，供 QA 校验与前端渲染。
"""

from __future__ import annotations

from typing import Any

from .analysis_contract import AnalysisFact, BpFinding, BpOutput, FactStatus


def run_bp_analysis(facts: list[AnalysisFact], contract: dict | None = None) -> BpOutput:
    """基于 Facts 生成 BP 输出。

    Args:
        facts: 各查询的确定性事实列表。
        contract: 口径快照（可选，用于限制说明）。
    """
    verified = [f for f in facts if f.status == FactStatus.VERIFIED]

    executive_summary: list[BpFinding] = []
    findings: list[BpFinding] = []
    limitations: list[str] = []
    next_questions: list[str] = []

    # 汇总类：生成执行摘要
    summary_facts = _by_category(verified, "summary")
    if summary_facts:
        for f in summary_facts[:3]:
            executive_summary.append(BpFinding(
                category="summary",
                text=_fact_text(f),
                fact_ids=[f.fact_id],
            ))

    # 趋势类
    trend_facts = _by_category(verified, "trend")
    direction = _find(trend_facts, "trend_direction")
    peak = _find(trend_facts, "trend_peak")
    if direction:
        findings.append(BpFinding(
            category="trend",
            text=f"趋势方向：{direction.display or direction.label}",
            fact_ids=[direction.fact_id],
        ))
    if peak:
        findings.append(BpFinding(
            category="trend",
            text=f"峰值：{peak.display or peak.label}",
            fact_ids=[peak.fact_id],
            query_ids=_query_ids_of(peak),
        ))

    # 结构/集中度
    structure_facts = _by_category(verified, "structure")
    if structure_facts:
        for f in structure_facts[:2]:
            findings.append(BpFinding(
                category="structure",
                text=f"结构：{f.display or f.label}",
                fact_ids=[f.fact_id],
            ))

    # 排名
    ranking_facts = _by_category(verified, "ranking")
    if ranking_facts:
        top = ranking_facts[0]
        findings.append(BpFinding(
            category="ranking",
            text=f"排名：{top.display or top.label}",
            fact_ids=[top.fact_id],
        ))

    # 对比/增长
    comparison_facts = _by_category(verified, "comparison")
    if comparison_facts:
        for f in comparison_facts[:2]:
            findings.append(BpFinding(
                category="comparison",
                text=f"对比：{f.display or f.label}",
                fact_ids=[f.fact_id],
            ))

    # 异常
    anomaly_facts = _by_category(verified, "anomaly")
    if anomaly_facts:
        for f in anomaly_facts[:2]:
            findings.append(BpFinding(
                category="anomaly",
                text=f"异常：{f.display or f.label}",
                fact_ids=[f.fact_id],
            ))

    # 数据不足的事实 -> 限制说明
    insufficient = [f for f in facts if f.status == FactStatus.DATA_INSUFFICIENT]
    for f in insufficient[:3]:
        limitations.append(f"{f.label}: {f.reason or '数据不足'}")

    # 口径限制
    if contract:
        filters = contract.get("mandatory_filters") or []
        if filters:
            limitations.append(f"本次分析已应用强制过滤：{', '.join(filters)}")
        baseline = contract.get("comparison_baseline")
        if baseline:
            limitations.append(f"当前结果未包含比较基准（{baseline}），不能判断活动增量贡献。")
            next_questions.append(f"是否补充{baseline}同口径数据？")

    if not verified:
        limitations.append("当前结果数据不足，未生成可信发现。valid_facts=0")

    # Markdown 渲染
    markdown = _render_markdown(executive_summary, findings, limitations, next_questions)

    return BpOutput(
        executive_summary=executive_summary,
        findings=findings,
        limitations=limitations,
        next_questions=next_questions,
        markdown=markdown,
    )


def _by_category(facts: list[AnalysisFact], category: str) -> list[AnalysisFact]:
    return [f for f in facts if f.category == category and f.status == FactStatus.VERIFIED]


def _find(facts: list[AnalysisFact], fact_id_prefix: str) -> AnalysisFact | None:
    for f in facts:
        if f.fact_id.startswith(fact_id_prefix):
            return f
    return None


def _fact_text(f: AnalysisFact) -> str:
    return f"{f.label}: {f.display or f.value}"


def _query_ids_of(f: AnalysisFact) -> list[str]:
    # fact_id 无查询信息，返回空；由上层按需注入
    return []


def _render_markdown(
    summary: list[BpFinding],
    findings: list[BpFinding],
    limitations: list[str],
    next_questions: list[str],
) -> str:
    lines: list[str] = []
    if summary:
        lines.append("## 摘要")
        for s in summary:
            lines.append(f"- {s.text}")
    if findings:
        lines.append("## 关键发现")
        for f in findings:
            lines.append(f"- {f.text}")
    if limitations:
        lines.append("## 数据限制")
        for l in limitations:
            lines.append(f"- {l}")
    if next_questions:
        lines.append("## 下一步")
        for qn in next_questions:
            lines.append(f"- {qn}")
    return "\n".join(lines)