"""
AI2BI Q2 分析意图识别 — 判断一次提问是否需要进入分析链路。

职责：
1. 区分 knowledge / data_lookup / chart_only / analysis / topic_analysis / prediction / unsupported。
2. 纯取数、纯画图请求不触发分析，避免“只画图却有结论”。
3. 输出可持久化的意图快照，供前端解释“为什么这次没有结论”。

设计原则：
- 规则优先、模型兜底。第一版用关键词规则，避免引入额外 LLM 调用延迟。
- 判定结果必须可解释：记录命中的信号词与原因。
- 本模块不访问数据库、不调用 LLM，是纯函数。
"""

from __future__ import annotations

from typing import Any

# 明确展示/取数信号（触发 SimpleMode 的关键词）
_CHART_ONLY_WORDS = ("画图", "柱状图", "折线图", "饼图", "可视化", "展示出来", "做成图", "图表")
_DATA_LOOKUP_WORDS = ("多少", "列出", "查询", "明细", "总金额", "总额", "数量", "几条", "是多少", "什么值")

# 分析信号（触发 AnalysisMode 的关键词）
_ANALYSIS_WORDS = (
    "分析", "情况怎么样", "怎么样", "表现如何", "表现", "发现", "洞察", "解读",
    "异常", "原因", "为什么", "趋势解读", "解读一下", "评估", "复盘", "效果",
)

# 专题分析信号（触发 TopicAnalysis 的关键词）
_TOPIC_WORDS = (
    "最近", "活动效果", "效果如何", "客户活跃", "交易情况", "渠道变化", "客群表现",
    "近期", "运营情况", "业务情况", "专题", "复盘", "增长贡献",
)

# 预测信号（默认阻断）
_PREDICTION_WORDS = ("预测", "预计", "未来", "下月会达到", "预估", "会上升到", "会增长到")

# 知识问答信号（Metric/规则/口径问题）
_KNOWLEDGE_WORDS = ("口径", "定义", "是什么", "怎么算", "规则", "指标含义", "术语", "区别")


def classify_intent(question: str) -> dict[str, Any]:
    """识别一次提问的分析意图，返回可持久化的意图快照。

    Returns:
        {
            "intent_type": str,
            "analysis_required": bool,
            "chart_required": bool,
            "contract_required": bool,
            "confidence": float,
            "reason": str,
            "signals": list[str],
        }
    """
    if not question:
        return _make("unsupported", False, False, False, 1.0, "问题为空", [])

    q = question.strip()
    has_analysis = _has_any(q, _ANALYSIS_WORDS)
    has_topic = _has_any(q, _TOPIC_WORDS)
    has_chart = _has_any(q, _CHART_ONLY_WORDS)
    has_lookup = _has_any(q, _DATA_LOOKUP_WORDS)
    has_prediction = _has_any(q, _PREDICTION_WORDS)
    has_knowledge = _has_any(q, _KNOWLEDGE_WORDS)

    signals: list[str] = []
    for name, hit in (
        ("prediction", has_prediction),
        ("topic", has_topic),
        ("analysis", has_analysis),
        ("chart", has_chart),
        ("lookup", has_lookup),
        ("knowledge", has_knowledge),
    ):
        if hit:
            signals.append(name)

    # 优先级：预测 > 专题 > 分析 > 知识 > 画图 > 取数
    if has_prediction:
        return _make(
            "prediction", False, False, False, 0.9,
            "用户请求数值预测，当前默认不提供未来数值预测。",
            signals,
        )
    if has_topic and (has_analysis or "效果" in q or "情况" in q):
        return _make(
            "topic_analysis", True, True, True, 0.85,
            "用户提出业务专题问题，需要多查询取数并输出发现。",
            signals,
        )
    if has_analysis:
        return _make(
            "analysis", True, True, has_lookup or has_topic, 0.8,
            "用户提出分析诉求，进入分析链路。",
            signals,
        )
    if has_knowledge:
        return _make(
            "knowledge", False, False, False, 0.75,
            "用户询问口径/定义，走知识问答，不执行 SQL。",
            signals,
        )
    if has_chart:
        return _make(
            "chart_only", False, True, False, 0.8,
            "用户只要求画图展示，未提出分析诉求，不产出经营结论。",
            signals,
        )
    if has_lookup:
        return _make(
            "data_lookup", False, False, False, 0.75,
            "用户只要求取数/查询，未提出分析诉求，不产出经营结论。",
            signals,
        )
    return _make(
        "unsupported", False, False, False, 0.5,
        "无法明确识别意图，需进一步澄清。",
        signals,
    )


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)


def _make(
    intent_type: str,
    analysis_required: bool,
    chart_required: bool,
    contract_required: bool,
    confidence: float,
    reason: str,
    signals: list[str],
) -> dict[str, Any]:
    return {
        "intent_type": intent_type,
        "analysis_required": analysis_required,
        "chart_required": chart_required,
        "contract_required": contract_required,
        "confidence": confidence,
        "reason": reason,
        "signals": signals,
    }