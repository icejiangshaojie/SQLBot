"""
AI2BI Q3 专题分析模板 — 定义业务专题所需的数据采集计划。

每个模板描述：
- 面向的业务问题（触发关键词）
- 需要采集的指标、维度、时间粒度、过滤条件
- 计划查询（summary / trend / breakdown），每个查询的目的与是否必需
- 允许的分析算子与结论边界

设计原则：
- 模板是"数据需求清单"，不包含具体 SQL（SQL 由网络生成或模板绑定）。
- 口径不明确时，返回 needs_confirmation，不静默执行。
- 模板只做两个起步专题，避免过早泛化。
"""

from __future__ import annotations

from typing import Any


# 每个模板的查询定义
_TOPIC_TEMPLATES: dict[str, dict[str, Any]] = {
    "card_transaction_overview": {
        "label": "卡交易近期情况",
        "triggers": ["卡交易", "交易情况", "消费情况", "近期", "卡消费"],
        "metrics": ["消费金额", "交易笔数", "活跃客户数"],
        "dimensions": ["渠道", "地区", "客群"],
        "mandatory_filters": ["成功授权", "排除ATM"],
        "operators": ["summary", "trend", "ranking", "structure"],
        "queries": [
            {"query_id": "summary", "purpose": "期间卡交易汇总（金额/笔数/客户数）", "required": True},
            {"query_id": "trend", "purpose": "按日/周/月的交易趋势", "required": False},
            {"query_id": "breakdown", "purpose": "按渠道/地区/客群的结构拆解", "required": False},
        ],
        "limits": {"max_queries": 3, "max_rows_per_query": 1000, "timeout_seconds": 60},
    },
    "campaign_effect_review": {
        "label": "卡活动效果复盘",
        "triggers": ["活动效果", "活动复盘", "营销活动", "效果如何", "活动表现"],
        "metrics": ["消费金额", "活跃客户数", "活动参与客户数"],
        "dimensions": ["活动分组", "渠道", "客群"],
        "mandatory_filters": ["成功授权", "活动标识"],
        "operators": ["summary", "trend", "ranking", "structure"],
        "queries": [
            {"query_id": "summary", "purpose": "活动期间汇总（金额/客户/参与）", "required": True},
            {"query_id": "trend", "purpose": "活动期间每日趋势", "required": False},
            {"query_id": "breakdown", "purpose": "按活动/渠道/客群效果拆解", "required": False},
        ],
        "limits": {"max_queries": 3, "max_rows_per_query": 1000, "timeout_seconds": 60},
    },
}


def list_topic_templates() -> list[str]:
    """返回已定义的专题模板 ID。"""
    return list(_TOPIC_TEMPLATES.keys())


def get_topic_template(template_id: str) -> dict[str, Any] | None:
    """按 ID 取专题模板定义；不存在返回 None。"""
    return _TOPIC_TEMPLATES.get(template_id)


def match_topic_template(question: str) -> tuple[str | None, dict[str, Any] | None]:
    """按问题关键词匹配专题模板，返回 (template_id, template)。"""
    q = question or ""
    for tid, tpl in _TOPIC_TEMPLATES.items():
        if any(kw in q for kw in tpl.get("triggers", [])):
            return tid, tpl
    return None, None