"""
AI2BI Phase 0 后端测试 — 确定性分析引擎、QA 合同、Evidence Pack。

仅测试纯函数，不依赖真实数据库或真实 LLM。
运行方式（在项目根目录）：
    python -m pytest tests/test_ai2bi_phase0.py -v
"""

import os
import sys
import json

# 将 backend 加入 path，以便 import AI2BI 模块
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from apps.ai2bi.analysis_engine import analyze_result  # noqa: E402
from apps.ai2bi.qa_checker import run_full_qa, run_result_qa  # noqa: E402
from apps.ai2bi.evidence_builder import build_evidence_pack, evidence_pack_to_prompt  # noqa: E402
from apps.ai2bi.analysis_contract import (  # noqa: E402
    AnalysisResult, AnalysisStatus, FactSource, FactStatus,
)


# ── 分析引擎 ──────────────────────────────────────

def test_engine_empty_result():
    facts = analyze_result({"fields": ["a"], "data": []})
    assert len(facts) == 1
    assert facts[0].status == FactStatus.DATA_INSUFFICIENT
    assert "空" in facts[0].label


def test_engine_single_row_direct():
    facts = analyze_result({"fields": ["total_amt"], "data": [{"total_amt": 1234567.89}]})
    assert len(facts) == 1
    assert facts[0].fact_id == "direct_total_amt"
    assert facts[0].source_type == FactSource.SQL
    assert facts[0].status == FactStatus.VERIFIED


def test_engine_trend():
    facts = analyze_result({
        "fields": ["dt", "amt"],
        "data": [
            {"dt": "2026-07-01", "amt": 100},
            {"dt": "2026-07-02", "amt": 200},
            {"dt": "2026-07-03", "amt": 150},
        ],
    })
    ids = [f.fact_id for f in facts]
    assert "trend_direction" in ids
    assert "trend_peak" in ids
    assert "trend_trough" in ids
    trend = next(f for f in facts if f.fact_id == "trend_direction")
    assert trend.source_type == FactSource.BACKEND


def test_engine_ranking():
    facts = analyze_result({
        "fields": ["cust_name", "trans_amt"],
        "data": [
            {"cust_name": "A", "trans_amt": 100},
            {"cust_name": "B", "trans_amt": 50},
            {"cust_name": "C", "trans_amt": 25},
        ],
    })
    ids = [f.fact_id for f in facts]
    assert "rank_trans_amt_1" in ids
    assert "top5_share" in ids


def test_engine_zero_denominator_no_growth():
    facts = analyze_result({
        "fields": ["period", "amt"],
        "data": [
            {"period": "6月", "amt": 0},
            {"period": "7月", "amt": 100},
        ],
    })
    growth = next((f for f in facts if f.fact_id == "growth_amt"), None)
    assert growth is not None
    assert growth.status == FactStatus.DATA_INSUFFICIENT


def test_engine_null_and_string_numeric():
    facts = analyze_result({
        "fields": ["amt"],
        "data": [
            {"amt": "1,234.56"},
            {"amt": None},
            {"amt": 100},
        ],
    })
    # 字符串数值被解析，NULL 被跳过
    assert any(f.fact_id == "sum_amt" for f in facts)


def test_engine_anomaly_insufficient():
    facts = analyze_result({
        "fields": ["dt", "amt"],
        "data": [{"dt": f"2026-07-{i:02d}", "amt": i} for i in range(1, 6)],
    })
    anomaly = next((f for f in facts if f.fact_id == "anomaly_iqr"), None)
    assert anomaly is not None
    assert anomaly.status == FactStatus.DATA_INSUFFICIENT


# ── QA 合同 ───────────────────────────────────────

def test_qa_passed():
    result = {"fields": ["total"], "data": [{"total": 100}]}
    facts = analyze_result(result)
    pack = build_evidence_pack("SELECT 1", result, {"agent": {}}, facts=facts)
    qa = run_full_qa("SELECT 1", result, "总额为 100 [SQL]。", pack, facts, {})
    assert qa.status == "passed"
    assert qa.renderable is True


def test_qa_blocked_unsourced():
    result = {"fields": ["total"], "data": [{"total": 100}]}
    facts = analyze_result(result)
    pack = build_evidence_pack("SELECT 1", result, {"agent": {}}, facts=facts)
    qa = run_full_qa("SELECT 1", result, "总额为 5000000，毫无根据。", pack, facts, {})
    assert qa.status == "blocked"
    assert qa.renderable is False
    assert any(f.code == "unsourced_numbers" for f in qa.findings)


def test_qa_detail_value_in_raw_data_is_sourced():
    """明细取值（100.0/607.0）存在于原始 result.data 但不在聚合 Facts 中，不应被判为无来源。"""
    result = {
        "fields": ["cust_id", "amt"],
        "data": [
            {"cust_id": "A", "amt": 100.0},
            {"cust_id": "B", "amt": 607.0},
            {"cust_id": "C", "amt": 607.0},
        ],
    }
    # 只聚合出少量事实，模拟明细未进 Facts 的场景
    facts = analyze_result({"fields": ["amt"], "data": [{"amt": 1314.0}]})
    pack = build_evidence_pack("SELECT cust_id, amt FROM t", result, {"agent": {}}, facts=facts)
    qa = run_full_qa(
        "SELECT cust_id, amt FROM t",
        result,
        "客户 A 金额为 100.0，客户 B 与 C 均为 607.0。",
        pack,
        facts,
        {},
    )
    assert qa.status == "passed", qa.findings


def test_qa_blocked_prediction():
    result = {"fields": ["total"], "data": [{"total": 100}]}
    facts = analyze_result(result)
    pack = build_evidence_pack("SELECT 1", result, {"agent": {}}, facts=facts)
    qa = run_full_qa("SELECT 1", result, "预计未来将达到 1000。", pack, facts, {})
    assert qa.status == "blocked"


def test_qa_result_insufficient():
    facts = analyze_result({"fields": ["a"], "data": []})
    qa = run_result_qa("SELECT 1", {"fields": ["a"], "data": []}, facts)
    assert any(f.code == "result_empty" for f in qa.findings)


# ── Evidence Pack ─────────────────────────────────

def test_evidence_pack_includes_facts():
    result = {"fields": ["total_amt"], "data": [{"total_amt": 1234567.89}]}
    facts = analyze_result(result)
    pack = build_evidence_pack("SELECT sum(total_amt) FROM t", result, {"agent": {"name": "deposit"}}, facts=facts)
    assert len(pack["facts"]) == 1
    prompt = evidence_pack_to_prompt(pack)
    assert "verified_facts" in prompt


def test_analysis_result_serializable():
    result = {"fields": ["a"], "data": [{"a": 1}]}
    facts = analyze_result(result)
    ar = AnalysisResult(status=AnalysisStatus.COMPLETED, facts=facts, final_text="分析文本")
    d = json.loads(json.dumps(ar.model_dump(mode="json")))
    assert d["status"] == "completed"
    assert d["final_text"] == "分析文本"
    assert len(d["facts"]) == 1