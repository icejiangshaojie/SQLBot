"""
AI2BI Q3 专题分析测试 — 计划器、编排器、BP Agent、QA。

仅测试纯函数，不依赖真实数据库或真实 LLM。
运行方式（在项目根目录）：
    python -m pytest tests/test_ai2bi_q3.py -v
"""

import os
import sys

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from apps.ai2bi.analysis_planner import build_topic_contract, build_topic_plan  # noqa: E402
from apps.ai2bi.analysis_orchestrator import run_topic_plan  # noqa: E402
from apps.ai2bi.bp_agent import run_bp_analysis  # noqa: E402
from apps.ai2bi.qa_checker import run_bp_qa  # noqa: E402
from apps.ai2bi.analysis_contract import AnalysisStatus, AnalysisFact, FactSource, FactStatus  # noqa: E402


# ── 计划器 ────────────────────────────────────────

def test_topic_contract_matches_card_transaction():
    c = build_topic_contract("最近卡交易情况怎么样")
    assert c.intent_type == "topic_analysis"
    assert c.topic_template == "card_transaction_overview"
    assert c.status == "confirmed"
    assert "消费金额" in c.metrics


def test_topic_contract_matches_campaign():
    c = build_topic_contract("最近卡活动效果如何")
    assert c.topic_template == "campaign_effect_review"
    assert c.comparison_baseline is not None


def test_topic_contract_needs_confirmation():
    c = build_topic_contract("今天天气怎么样")
    assert c.status == "needs_confirmation"


def test_topic_plan_generates_queries():
    p = build_topic_plan("最近卡交易情况怎么样")
    assert len(p.queries) == 3
    ids = [q.query_id for q in p.queries]
    assert ids == ["summary", "trend", "breakdown"]
    assert p.queries[0].required is True


def test_topic_plan_no_template_empty():
    p = build_topic_plan("今天天气怎么样")
    assert p.queries == []


# ── 编排器 ────────────────────────────────────────

def _fake_gen(question, ctx, purpose):
    return f"SELECT 1 -- {purpose}"


def _fake_exec(sql):
    if "汇总" in sql:
        return {"fields": ["total_amt", "trans_cnt"], "data": [{"total_amt": 1234567.0, "trans_cnt": 890}]}
    if "趋势" in sql:
        return {"fields": ["dt", "amt"], "data": [
            {"dt": "2026-07-01", "amt": 100.0},
            {"dt": "2026-07-02", "amt": 150.0},
            {"dt": "2026-07-03", "amt": 120.0},
        ]}
    return {"fields": ["channel", "amt"], "data": [
        {"channel": "online", "amt": 500.0},
        {"channel": "pos", "amt": 300.0},
    ]}


def test_orchestrator_runs_all_queries():
    p = build_topic_plan("最近卡交易情况怎么样")
    r = run_topic_plan(p, "最近卡交易情况怎么样", "", _fake_gen, _fake_exec)
    assert r.status == AnalysisStatus.COMPLETED
    assert len(r.facts) > 0
    completed = [q for q in p.queries if q.status == "completed"]
    assert len(completed) == 3


def test_orchestrator_required_failure_fails():
    def _bad_exec(sql):
        raise RuntimeError("db down")
    p = build_topic_plan("最近卡交易情况怎么样")
    r = run_topic_plan(p, "最近卡交易情况怎么样", "", _fake_gen, _bad_exec)
    assert r.status == AnalysisStatus.FAILED


def test_orchestrator_optional_failure_degrades():
    def _partial_exec(sql):
        if "汇总" in sql:
            return {"fields": ["total_amt"], "data": [{"total_amt": 999.0}]}
        raise RuntimeError("optional query failed")
    p = build_topic_plan("最近卡交易情况怎么样")
    r = run_topic_plan(p, "最近卡交易情况怎么样", "", _fake_gen, _partial_exec)
    assert r.status == AnalysisStatus.COMPLETED
    assert len(r.facts) >= 1


def test_orchestrator_empty_result_data_insufficient():
    def _empty_exec(sql):
        return {"fields": ["a"], "data": []}
    p = build_topic_plan("最近卡交易情况怎么样")
    r = run_topic_plan(p, "最近卡交易情况怎么样", "", _fake_gen, _empty_exec)
    assert r.status == AnalysisStatus.DATA_INSUFFICIENT


# ── BP Agent ──────────────────────────────────────

def _facts():
    return [
        AnalysisFact(fact_id="sum_total_amt", category="summary", label="消费金额合计",
                     value=1234567.0, source_type=FactSource.SQL, status=FactStatus.VERIFIED),
        AnalysisFact(fact_id="trend_direction", category="trend", label="趋势方向",
                     value=20.0, source_type=FactSource.BACKEND, display="上升",
                     status=FactStatus.VERIFIED),
        AnalysisFact(fact_id="trend_peak", category="trend", label="峰值",
                     value=150.0, source_type=FactSource.SQL, status=FactStatus.VERIFIED),
        AnalysisFact(fact_id="top5_share", category="structure", label="Top5集中度",
                     value=0.8, source_type=FactSource.BACKEND, display="80.0%",
                     status=FactStatus.VERIFIED),
    ]


def test_bp_generates_findings():
    bp = run_bp_analysis(_facts())
    assert len(bp.executive_summary) >= 1
    assert len(bp.findings) >= 3  # trend + structure
    assert bp.markdown


def test_bp_marks_limitations_when_no_facts():
    bp = run_bp_analysis([])
    assert bp.findings == []
    assert any("数据不足" in l for l in bp.limitations)


def test_bp_qa_passes_with_valid_facts():
    bp = run_bp_analysis(_facts())
    qa = run_bp_qa(bp, _facts())
    assert qa.status == "passed"
    assert qa.renderable is True


def test_bp_qa_blocks_output_without_facts():
    bp = run_bp_analysis([])
    # 强制构造一个无事实引用但有发现的输出 -> block
    from apps.ai2bi.analysis_contract import BpOutput, BpFinding
    bad = BpOutput(
        executive_summary=[BpFinding(category="summary", text="总额100万", fact_ids=[])],
    )
    qa = run_bp_qa(bad, [])
    assert qa.status == "blocked"
    assert qa.renderable is False


def test_bp_qa_warns_invalid_fact_ref():
    from apps.ai2bi.analysis_contract import BpOutput, BpFinding
    bp = BpOutput(findings=[BpFinding(category="trend", text="某发现", fact_ids=["nonexistent_fact"])])
    qa = run_bp_qa(bp, _facts())
    assert qa.status == "warning"