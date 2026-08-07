"""
AI2BI Q2 意图门控测试 — 分析意图识别。

仅测试纯函数，不依赖真实数据库或真实 LLM。
运行方式（在项目根目录）：
    python -m pytest tests/test_ai2bi_intent.py -v
"""

import os
import sys

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from apps.ai2bi.analysis_intent import classify_intent  # noqa: E402


# ── 纯画图：不触发分析 ─────────────────────────────

def test_chart_only_does_not_require_analysis():
    r = classify_intent("用柱状图展示7月每日消费金额趋势")
    assert r["intent_type"] == "chart_only"
    assert r["analysis_required"] is False
    assert r["chart_required"] is True
    assert "展示趋势图" in r["reason"] or "画图" in r["reason"]


def test_chart_only_keeps_chart_but_skips_analysis():
    r = classify_intent("画折线图看近期交易波动")
    assert r["intent_type"] == "chart_only"
    assert r["analysis_required"] is False


# ── 纯取数：不触发分析 ─────────────────────────────

def test_data_lookup_does_not_require_analysis():
    r = classify_intent("7月消费总金额是多少")
    assert r["intent_type"] == "data_lookup"
    assert r["analysis_required"] is False


def test_data_lookup_query_words():
    r = classify_intent("查询系统注册用户数量")
    assert r["intent_type"] == "data_lookup"
    assert r["analysis_required"] is False


# ── 明确分析：触发 ─────────────────────────────────

def test_analysis_requires_analysis():
    r = classify_intent("7月卡消费情况怎么样")
    assert r["intent_type"] == "analysis"
    assert r["analysis_required"] is True


def test_analysis_detected_by_analysis_word():
    r = classify_intent("分析下7月消费金额异常的原因")
    assert r["analysis_required"] is True


# ── 专题分析：触发且需多查询 ───────────────────────

def test_topic_analysis_requires_contract():
    r = classify_intent("最近卡交易情况怎么样")
    assert r["intent_type"] == "topic_analysis"
    assert r["analysis_required"] is True
    assert r["contract_required"] is True


def test_campaign_effect_review():
    r = classify_intent("最近卡活动效果如何")
    assert r["intent_type"] == "topic_analysis"
    assert r["analysis_required"] is True


# ── 知识问答：不触发 SQL 分析 ──────────────────────

def test_knowledge_question():
    r = classify_intent("日均余额口径是什么")
    assert r["intent_type"] == "knowledge"
    assert r["analysis_required"] is False


# ── 预测：默认阻断 ─────────────────────────────────

def test_prediction_blocked():
    r = classify_intent("预测下月卡消费金额")
    assert r["intent_type"] == "prediction"
    assert r["analysis_required"] is False


# ── 空与兜底 ───────────────────────────────────────

def test_empty_question_unsupported():
    r = classify_intent("")
    assert r["intent_type"] == "unsupported"
    assert r["analysis_required"] is False


def test_intent_snapshot_serializable():
    """意图快照应可 JSON 序列化（持久化到 Evidence）。"""
    import json
    r = classify_intent("用柱状图展示7月每日消费金额趋势")
    json.dumps(r)
    assert "reason" in r
    assert "signals" in r