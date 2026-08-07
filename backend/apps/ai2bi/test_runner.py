"""
AI2BI Test Runner — 回归测试执行器

三种测试类型：
1. routing: 验证问题是否路由到正确 Agent
2. sql_regression: 验证生成的 SQL 是否包含正确表/分区/过滤
3. evidence: 验证回答中数字是否有证据来源

Agent 发布前自动运行测试集，全部通过才允许发布。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlmodel import Session, select
from common.core.db import engine

logger = logging.getLogger(__name__)

# AIBI_v2 知识库根目录（已并入 SQLBot/knowledge/AIBI_v2）
import os
AIBI_V2_ROOT = Path(os.environ.get(
    "AIBI_V2_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "knowledge", "AIBI_v2")
)).resolve()


def run_routing_test(question: str, expected_agent: Optional[str]) -> dict:
    """运行路由测试：验证问题是否路由到正确 Agent"""
    from apps.ai2bi.skill_router import route_question

    result = route_question(question)
    actual_agent = result.get("agent", {})
    actual_code = actual_agent.get("code") if actual_agent else None

    if expected_agent is None:
        # 期望未命中（负例）
        passed = result.get("is_fallback", True)
        return {
            "passed": passed,
            "actual": "fallback" if result.get("is_fallback") else actual_code,
            "expected": "fallback (no agent)",
        }

    passed = actual_code == expected_agent
    return {
        "passed": passed,
        "actual": actual_code or "fallback",
        "expected": expected_agent,
        "confidence": result.get("confidence", 0),
        "sub_skill": result.get("sub_skill"),
    }


def run_sql_regression_test(question: str, expected_tables: list[str],
                             expected_sql_patterns: list[str]) -> dict:
    """
    运行 SQL 回归测试：验证路由后加载的表白名单和规则是否正确。

    注意：这不会实际执行 SQL（需要 LLM 调用），只验证路由结果的表白名单。
    完整 SQL 测试需要手动在 Skill 开发页运行。
    """
    from apps.ai2bi.skill_router import route_question

    result = route_question(question)

    # 检查路由命中的表白名单是否包含预期的表
    available_tables = set(result.get("exclusive_tables", []) + result.get("shared_tables", []))
    missing_tables = [t for t in expected_tables if t not in available_tables]

    # 检查 context_prompt 是否包含预期的 SQL 模式
    context = result.get("context_prompt", "")
    missing_patterns = [p for p in expected_sql_patterns if p.lower() not in context.lower()]

    passed = len(missing_tables) == 0 and len(missing_patterns) == 0

    return {
        "passed": passed,
        "available_tables": list(available_tables),
        "missing_tables": missing_tables,
        "missing_patterns": missing_patterns,
        "is_fallback": result.get("is_fallback", True),
    }


def run_evidence_test(question: str, expected_evidence_count: int,
                      forbid_model_inferred: bool = True) -> dict:
    """
    运行证据测试：验证回答中的数字是否有证据来源。

    注意：这需要实际执行 LLM 问答，目前返回占位结果。
    完整证据测试需要手动在聊天页运行后查看证据链。
    """
    # 占位：完整测试需要调用 LLM 生成 SQL → 执行 → 分析 → 质检
    # 目前只返回路由信息
    from apps.ai2bi.skill_router import route_question
    result = route_question(question)

    return {
        "passed": None,  # 需要实际运行才能判断
        "note": "证据测试需要实际执行问答，当前仅返回路由信息",
        "routed_agent": result.get("agent", {}).get("code") if result.get("agent") else None,
        "is_fallback": result.get("is_fallback", True),
    }


def run_test_cases_for_agent(agent_id: int) -> dict:
    """
    运行指定 Agent 的所有测试用例。

    返回: {total, passed, failed, details}
    """
    from apps.ai2bi.test_models import Ai2biTestCase, Ai2biTestRun

    results = []
    now = datetime.now()

    with Session(engine) as s:
        cases = s.exec(
            select(Ai2biTestCase).where(Ai2biTestCase.agent_id == agent_id)
        ).all()

    for case in cases:
        detail = {"question": case.question, "test_type": case.test_type}

        try:
            if case.test_type == "routing":
                expected_agent = case.expected_agent
                expected_tables = json.loads(case.expected_tables) if case.expected_tables else []
                r = run_routing_test(case.question, expected_agent)
                detail.update(r)
                passed = r["passed"]

            elif case.test_type == "sql_regression":
                expected_tables = json.loads(case.expected_tables) if case.expected_tables else []
                expected_patterns = json.loads(case.expected_sql_pattern) if case.expected_sql_pattern else []
                r = run_sql_regression_test(case.question, expected_tables, expected_patterns)
                detail.update(r)
                passed = r["passed"]

            elif case.test_type == "evidence":
                r = run_evidence_test(case.question, case.expected_evidence_count)
                detail.update(r)
                passed = r.get("passed")  # 可能为 None

            else:
                passed = False
                detail["error"] = f"Unknown test type: {case.test_type}"

        except Exception as e:
            passed = False
            detail["error"] = str(e)

        # 更新 test case 记录
        with Session(engine) as s:
            tc = s.get(Ai2biTestCase, case.id)
            if tc:
                tc.last_run_at = now
                tc.last_passed = passed
                tc.last_result = json.dumps(detail, ensure_ascii=False, default=str)
                s.add(tc)
                s.commit()

        results.append(detail)

    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed") is True)
    failed_count = sum(1 for r in results if r.get("passed") is False)

    # 保存 test run 记录
    with Session(engine) as s:
        s.add(Ai2biTestRun(
            agent_id=agent_id,
            total=total,
            passed=passed_count,
            failed=failed_count,
            details=json.dumps(results, ensure_ascii=False, default=str),
            run_at=now,
        ))
        s.commit()

    return {
        "total": total,
        "passed": passed_count,
        "failed": failed_count,
        "pending": total - passed_count - failed_count,
        "details": results,
    }


def load_test_cases_from_file(agent_code: str) -> list[dict]:
    """从 AIBI_v2/test_cases/ 目录加载测试用例"""
    test_dir = AIBI_V2_ROOT / "test_cases" / agent_code.replace("_agent", "")
    if not test_dir.exists():
        return []

    cases = []
    for jsonl_file in test_dir.glob("*.jsonl"):
        test_type = jsonl_file.stem  # routing, sql_regression, evidence
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    case = json.loads(line)
                    case["test_type"] = test_type
                    cases.append(case)
                except json.JSONDecodeError:
                    continue

    return cases
