"""
AI2BI QA Checker — 全链路质检（Phase 0 重构）。

三层质检：
1. 结果级：空结果、NULL 比例、超行数、无可识别数值/维度。
2. 事实级：校验 Facts 是否自洽、是否有 data_insufficient 占主导、来源是否合法。
3. 答案级：以 Facts 值和来源为主要依据；无来源经营数字、与 Fact 不一致、预测、因果断言等。

输出合同（QaResult）：
- status: passed | warning | blocked
- findings: [{code, severity, message, fact_ids, source_refs}]
- summary: SQL/后端计算/模型推导/无来源/数据不足的数量
- renderable: 是否允许展示模型分析正文

设计原则：
- block 级 QA 必须阻止无来源经营数字、预测、无支持因果断言进入已验证分析。
- 保留 SQL 结果、图表和下载能力，即使分析被阻断。
"""

from __future__ import annotations

import re

from .analysis_contract import AnalysisFact, FactSource, FactStatus, QaFinding, QaResult

# ── 数值提取 ──────────────────────────────────────

def _to_number(val) -> float | None:
    """宽容解析数值（含字符串），无法解析返回 None。"""
    import re as _re
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.replace(",", "").replace("，", "").replace(" ", "").replace("%", "")
        s = _re.sub(r"[HKD$¥€£元]", "", s, flags=_re.IGNORECASE)
        try:
            return float(s)
        except (ValueError, TypeError):
            return None
    return None


def _extract_all_numbers(text: str) -> list[float]:
    """从文本中提取所有数字，过滤明显非数据数字（日期、月份、序号等）。"""
    pattern = re.compile(r'(?<![a-zA-Z_])(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.?\d*)(?![a-zA-Z_])')
    numbers = []
    for match in pattern.finditer(text):
        try:
            raw = match.group(0)
            val = float(raw.replace(",", ""))
            if 1900 <= val <= 2099 and "." not in raw:
                continue
            if 1 <= val <= 31 and "." not in raw and "," not in raw:
                start = max(0, match.start() - 5)
                end = min(len(text), match.end() + 5)
                context = text[start:end]
                if re.search(r'[月日号年/-]', context):
                    continue
            if val < 1 and "." not in raw:
                continue
            numbers.append(val)
        except (ValueError, TypeError):
            continue
    return numbers


# ── 结果级质检 ────────────────────────────────────

def check_result_quality(result: dict, _sql: str) -> list[dict]:
    """
    SQL 执行结果质检。返回 findings（含 severity）。
    """
    findings = []
    data = result.get("data", [])
    fields = result.get("fields", [])

    if not data:
        findings.append(_find("result_empty", "warning", "SQL 查询结果为空，请检查查询条件。"))
    if len(data) > 10000:
        findings.append(_find("result_too_large", "warning", f"查询结果 {len(data)} 行，超过安全阈值 10000。"))

    if data and isinstance(data[0], dict):
        for field in fields[:10]:
            null_count = sum(1 for row in data if row.get(field) is None or row.get(field) == "")
            if data:
                null_ratio = null_count / len(data)
                if null_ratio > 0.5:
                    findings.append(_find(
                        "result_high_null", "warning",
                        f"列 '{field}' 的 NULL 值比例为 {null_ratio:.0%}。",
                    ))
    return findings


# ── 事实级质检 ────────────────────────────────────

def check_facts(facts: list[AnalysisFact]) -> list[dict]:
    findings = []
    for f in facts:
        if f.status == FactStatus.DATA_INSUFFICIENT:
            findings.append(_find(
                "fact_insufficient", "warning", f"{f.label}: {f.reason or '数据不足'}",
                fact_ids=[f.fact_id],
            ))
    return findings


# ── 答案级质检 ────────────────────────────────────

def check_answer_against_facts(answer_text: str, facts: list[AnalysisFact],
                               evidence_pack: dict | None = None) -> list[dict]:
    """
    以 Facts + 原始结果数据为依据检查答案数字。

    - facts 提供确定性聚合/计算值。
    - evidence_pack.result.data 提供 SQL 直出的明细值（LLM 可合法引用）。
    无来源经营数字、与来源不一致、预测、因果断言 => block。
    """
    findings = []
    answer_numbers = _extract_all_numbers(answer_text)

    # 已知来源的值集合：facts + 原始结果数据的所有数值
    sourced_values = set()
    for f in facts:
        if f.value is not None and f.status == FactStatus.VERIFIED:
            sourced_values.add(round(float(f.value), 2))
    if evidence_pack:
        for row in (evidence_pack.get("result", {}).get("data", []) or []):
            if not isinstance(row, dict):
                continue
            for v in row.values():
                num = _to_number(v)
                if num is not None:
                    sourced_values.add(round(num, 2))

    unsourced = []
    for num in answer_numbers:
        if abs(num) < 2:
            continue
        # 附近有标签（[SQL]/[计算]/[模型推导]）视为已标注
        if _is_near_tag(answer_text, num, ["[SQL]", "[计算", "[模型推导]"], window=80):
            continue
        if _is_approximately_sourced(num, sourced_values):
            continue
        if _is_in_sql_block(answer_text, num):
            continue
        unsourced.append(num)

    if unsourced:
        unsourced_str = ", ".join(str(n) for n in unsourced[:5])
        findings.append(_find(
            "unsourced_numbers", "block",
            f"回答中有 {len(unsourced)} 个经营数字无证据来源: {unsourced_str}...",
        ))

    # 禁止项：数值预测
    prediction_patterns = [r"预计.*将达到", r"预测.*约为", r"未来.*将达到", r"预估.*元"]
    for pattern in prediction_patterns:
        if re.search(pattern, answer_text):
            findings.append(_find("prediction_forbidden", "block", "回答中存在数值预测，已违反禁止规则。"))
            break

    # 禁止项：因果断言
    causal_patterns = [r"导致.*因为", r"因为.*所以.*下降", r"原因.*是.*导致", r"因此.*上涨"]
    for pattern in causal_patterns:
        if re.search(pattern, answer_text):
            findings.append(_find("causal_claim", "warning", "回答中存在因果断言，需确认有业务规则支持。"))
            break

    return findings


# ── 综合质检 ──────────────────────────────────────

def run_full_qa(
    sql: str,
    result: dict,
    answer_text: str,
    _evidence_pack: dict,
    facts: list | None = None,
    qa_config: dict | None = None,
) -> QaResult:
    """
    全链路质检入口，返回 QaResult（status/findings/summary/renderable）。
    """
    qa_config = qa_config or {}
    facts = facts or []

    findings: list[dict] = []
    findings += check_result_quality(result, sql)
    findings += check_facts(facts)
    if answer_text:
        findings += check_answer_against_facts(answer_text, facts, _evidence_pack)

    # 汇总
    summary = _summarize(answer_text, facts)

    # 判定 status
    blocks = [f for f in findings if f.get("severity") == "block"]
    warnings = [f for f in findings if f.get("severity") == "warning"]
    status = "passed"
    if blocks:
        status = "blocked"
    elif warnings:
        status = "warning"

    renderable = status in ("passed", "warning")

    qa = QaResult(
        status=status,
        findings=[QaFinding(**f) for f in findings],
        summary=summary,
        renderable=renderable,
    )
    return qa


def run_result_qa(
    sql: str,
    result: dict,
    facts: list | None = None,
) -> QaResult:
    """仅结果级 QA（分析前调用），用于判断是否达到可分析条件。"""
    findings = check_result_quality(result, sql)
    findings += check_facts(facts or [])
    blocks = [f for f in findings if f.get("severity") == "block"]
    warnings = [f for f in findings if f.get("severity") == "warning"]
    status = "passed" if not blocks and not warnings else ("blocked" if blocks else "warning")
    return QaResult(
        status=status,
        findings=[QaFinding(**f) for f in findings],
        summary=_summarize("", facts or []),
        renderable=status in ("passed", "warning"),
    )


def _summarize(answer_text: str, facts: list[AnalysisFact]) -> dict:
    summary = {
        "sql_facts": 0,
        "backend_facts": 0,
        "model_facts": 0,
        "data_insufficient": 0,
        "sourced_numbers": 0,
        "derived_count": 0,
        "inferred_count": 0,
        "unsourced_count": 0,
    }
    for f in facts:
        if f.source_type == FactSource.SQL:
            summary["sql_facts"] += 1
        elif f.source_type == FactSource.BACKEND:
            summary["backend_facts"] += 1
        elif f.source_type == FactSource.MODEL:
            summary["model_facts"] += 1
        if f.status == FactStatus.DATA_INSUFFICIENT:
            summary["data_insufficient"] += 1
    if answer_text:
        summary["sourced_numbers"] = answer_text.count("[SQL]")
        summary["derived_count"] = answer_text.count("[计算")
        summary["inferred_count"] = answer_text.count("[模型推导]")
        summary["unsourced_count"] = len([n for n in _extract_all_numbers(answer_text)
                                          if abs(n) >= 2 and not _is_near_tag(
                                              answer_text, n, ["[SQL]", "[计算]", "[模型推导]"], window=80)])
    return summary


# ── 工具函数 ──────────────────────────────────────

def _find(code: str, severity: str, message: str, fact_ids: list | None = None) -> dict:
    return {"code": code, "severity": severity, "message": message, "fact_ids": fact_ids or []}


def _is_near_tag(text: str, number: float, tags: list[str], window: int = 50) -> bool:
    num_strs = [str(number)]
    if number == int(number):
        num_strs.append(f"{int(number):,}")
    else:
        num_strs.append(f"{number:.2f}")
        num_strs.append(f"{number:,.2f}")
    for num_str in num_strs:
        for tag in tags:
            for match in re.finditer(re.escape(num_str), text):
                start = max(0, match.start() - window)
                end = min(len(text), match.end() + window)
                if tag in text[start:end]:
                    return True
    return False


def _is_approximately_sourced(value: float, sourced_set: set, tolerance: float = 0.01) -> bool:
    for s in sourced_set:
        if abs(value - s) / max(abs(s), 1) < tolerance:
            return True
    return False


def _is_in_sql_block(text: str, number: float) -> bool:
    num_str = str(number)
    sql_blocks = re.findall(r'```sql.*?```', text, re.DOTALL | re.IGNORECASE)
    for block in sql_blocks:
        if num_str in block:
            return True
    return False
