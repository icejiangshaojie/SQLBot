"""
AI2BI Evidence Builder — 从 SQL 执行结果构建结构化证据包

职责：
1. 从 ODPS 查询结果提取所有数值，标注来源列和行号 → sourced_numbers
2. 从 SQL 文本提取分区信息、表名、过滤条件
3. 生成结果摘要（列名、行数、样本行）供分析 LLM 使用
4. 构建完整的 Evidence Pack，作为分析阶段的唯一数据输入

核心原则：Evidence Pack 是分析 LLM 的唯一数据来源。
分析 LLM 不能访问原始数据库，只能基于 Evidence Pack 中的数据做分析。
"""

import re
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── 数值提取 ──────────────────────────────────────

def extract_sourced_numbers(result: dict) -> list[dict]:
    """
    从 SQL 结果提取所有数值及其来源。

    每个 numeric 值记录：
    - value: 数值本身
    - source: "sql"
    - column: 所属列名
    - row_index: 行号
    """
    numbers = []
    data = result.get("data", [])
    fields = result.get("fields", [])

    for row_idx, row in enumerate(data[:100]):  # 限制 100 行避免过大
        if not isinstance(row, dict):
            continue
        for col, val in row.items():
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                numbers.append({
                    "value": val,
                    "source": "sql",
                    "column": col,
                    "row_index": row_idx,
                })
            elif isinstance(val, str):
                # 尝试解析字符串中的数值（如 "1,234,567.89"）
                parsed = _try_parse_numeric_string(val)
                if parsed is not None:
                    numbers.append({
                        "value": parsed,
                        "source": "sql",
                        "column": col,
                        "row_index": row_idx,
                        "original_string": val,
                    })
    return numbers


def _try_parse_numeric_string(val: str) -> Optional[float]:
    """尝试将字符串解析为数值，处理千分位逗号"""
    if not val or not any(c.isdigit() for c in val):
        return None
    cleaned = val.replace(",", "").replace("，", "").replace(" ", "").replace("%", "")
    # 去掉货币符号
    cleaned = re.sub(r"[HKD$¥€£]", "", cleaned, flags=re.IGNORECASE)
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


# ── SQL 信息提取 ──────────────────────────────────

def extract_tables_from_sql(sql: str) -> list[str]:
    """从 SQL 中提取表名（FROM / JOIN 后的表名）"""
    tables = []
    # 匹配 FROM table / JOIN table，忽略子查询
    pattern = re.compile(
        r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_\.]+)',
        re.IGNORECASE
    )
    for match in pattern.finditer(sql):
        table = match.group(1).strip("`").strip('"')
        # 跳过子查询的关键字
        if table.upper() in ("SELECT", "(", "WITH"):
            continue
        tables.append(table)
    return list(dict.fromkeys(tables))  # 去重保序


def extract_partition_info(sql: str) -> dict:
    """从 SQL 中提取分区条件"""
    info = {"has_pt": False, "pt_type": None, "pt_values": []}

    # pt = (SELECT MAX(pt)...) → 全量快照
    if re.search(r"pt\s*=\s*\(\s*SELECT\s+MAX\s*\(\s*pt", sql, re.IGNORECASE):
        info["has_pt"] = True
        info["pt_type"] = "max_snapshot"
        return info

    # pt BETWEEN 'start' AND 'end' → 增量范围
    between_match = re.search(
        r"pt\s+BETWEEN\s+['\"]?(\d+)['\"]?\s+AND\s+['\"]?(\d+)['\"]?",
        sql, re.IGNORECASE
    )
    if between_match:
        info["has_pt"] = True
        info["pt_type"] = "range"
        info["pt_values"] = [between_match.group(1), between_match.group(2)]
        return info

    # pt = 'value' → 固定分区
    eq_match = re.search(r"pt\s*=\s*['\"]?(\d+)['\"]?", sql, re.IGNORECASE)
    if eq_match:
        info["has_pt"] = True
        info["pt_type"] = "fixed"
        info["pt_values"] = [eq_match.group(1)]
        return info

    return info


def extract_filters_from_sql(sql: str) -> list[str]:
    """从 WHERE 子句提取关键过滤条件"""
    filters = []
    # 提取 is_successful_auth = 1
    if re.search(r"is_successful_auth\s*=\s*['\"]?1", sql, re.IGNORECASE):
        filters.append("is_successful_auth = 1 (成功授权)")
    # 提取 trans_channel <> ATM
    if re.search(r"trans_channel\s*<>\s*['\"]?ATM", sql, re.IGNORECASE):
        filters.append("trans_channel <> ATM (排除ATM)")
    return filters


# ── 结果摘要 ──────────────────────────────────────

def summarize_result(result: dict) -> dict:
    """生成 SQL 结果摘要（不含全部数据，只含结构和样本）"""
    data = result.get("data", [])
    fields = result.get("fields", [])

    # 样本行：前 5 行
    sample = []
    for row in data[:5]:
        if isinstance(row, dict):
            sample.append({k: v for k, v in list(row.items())[:10]})

    return {
        "columns": fields,
        "row_count": len(data),
        "sample_rows": sample,
    }


# ── Evidence Pack 构建 ────────────────────────────

def build_evidence_pack(
    sql: str,
    result: dict,
    route_info: dict,
    metric_context: Optional[list] = None,
) -> dict:
    """
    构建完整的 Evidence Pack，作为分析 LLM 的唯一数据输入。

    参数:
        sql: 已执行的 SQL 文本
        result: ODPS 执行结果 {fields, data}
        route_info: 路由信息 {agent, domain, sub_skill, confidence, is_fallback}
        metric_context: 涉及的指标定义列表

    返回:
        Evidence Pack dict
    """
    data = result.get("data", [])
    fields = result.get("fields", [])

    sourced_numbers = extract_sourced_numbers(result)
    tables = extract_tables_from_sql(sql)
    partition = extract_partition_info(sql)
    filters = extract_filters_from_sql(sql)
    summary = summarize_result(result)

    # 限制传入分析 LLM 的数据行数（避免 token 爆炸）
    data_for_llm = data[:100] if len(data) > 100 else data

    agent = route_info.get("agent") or {}

    pack = {
        "agent": {
            "code": agent.get("code"),
            "name": agent.get("name"),
            "vertical": agent.get("vertical"),
        },
        "route": {
            "is_fallback": route_info.get("is_fallback", True),
            "sub_skill": route_info.get("sub_skill"),
            "confidence": route_info.get("confidence", 0),
        },
        "sql": {
            "text": sql,
            "executed": True,
            "tables": tables,
            "partition": partition,
            "filters": filters,
        },
        "result": {
            "columns": fields,
            "row_count": len(data),
            "data": data_for_llm,
            "summary": summary,
        },
        "sourced_numbers": sourced_numbers,
        "metric_definitions": metric_context or [],
    }

    return pack


def evidence_pack_to_prompt(pack: dict) -> str:
    """将 Evidence Pack 格式化为 LLM 可读的 prompt 文本"""
    parts = []

    # Agent 信息
    agent = pack.get("agent", {})
    parts.append(f"<agent>{agent.get('name', '通用模式')} ({agent.get('vertical', 'fallback')})</agent>")

    # SQL 信息
    sql_info = pack.get("sql", {})
    parts.append(f"<executed_sql>\n{sql_info.get('text', '')}\n</executed_sql>")
    parts.append(f"<tables>{', '.join(sql_info.get('tables', []))}</tables>")

    pt = sql_info.get("partition", {})
    if pt.get("has_pt"):
        parts.append(f"<partition type=\"{pt.get('pt_type')}\">{', '.join(pt.get('pt_values', []))}</partition>")

    filters = sql_info.get("filters", [])
    if filters:
        parts.append(f"<filters>{'; '.join(filters)}</filters>")

    # 结果数据
    result = pack.get("result", {})
    parts.append(f"<result row_count=\"{result.get('row_count', 0)}\">")
    parts.append(f"columns: {', '.join(result.get('columns', []))}")

    data = result.get("data", [])
    if data:
        # 构建简化表格（前 50 行）
        for i, row in enumerate(data[:50]):
            if isinstance(row, dict):
                row_str = " | ".join(f"{k}={v}" for k, v in list(row.items())[:8])
                parts.append(f"  row[{i}]: {row_str}")
        if len(data) > 50:
            parts.append(f"  ... ({len(data) - 50} more rows)")
    parts.append("</result>")

    # 指标口径
    metrics = pack.get("metric_definitions", [])
    if metrics:
        parts.append("<metric_definitions>")
        for m in metrics:
            parts.append(f"  - {m.get('cn_name', '')}: {m.get('business_definition', '')}")
            if m.get("calculation"):
                parts.append(f"    计算: {m.get('calculation')}")
        parts.append("</metric_definitions>")

    # 已提取的数值证据
    sourced = pack.get("sourced_numbers", [])
    if sourced:
        parts.append(f"<sourced_numbers count=\"{len(sourced)}\">")
        for n in sourced[:30]:  # 限制显示前 30 个
            parts.append(f"  - {n['value']} (来源: {n['column']}, 行: {n.get('row_index', '?')})")
        if len(sourced) > 30:
            parts.append(f"  ... ({len(sourced) - 30} more)")
        parts.append("</sourced_numbers>")

    return "\n".join(parts)


# ── 证据记录保存 ──────────────────────────────────

def save_evidence_record(
    session,
    record_id: int,
    chat_id: int,
    route_info: dict,
    sql: str,
    result: dict,
    qa_passed: Optional[bool] = None,
    qa_violations: Optional[list] = None,
) -> Any:
    """保存证据记录到 DB"""
    from apps.ai2bi.evidence_models import Ai2biEvidence
    from datetime import datetime

    pack = build_evidence_pack(sql, result, route_info)
    agent = route_info.get("agent") or {}

    evidence = Ai2biEvidence(
        record_id=record_id,
        chat_id=chat_id,
        agent_id=agent.get("id"),
        route_info=json.dumps(route_info, ensure_ascii=False, default=str),
        sql_text=sql,
        sql_executed=True,
        sql_row_count=len(result.get("data", [])),
        sql_result_summary=json.dumps(pack["result"]["summary"], ensure_ascii=False, default=str),
        sourced_numbers=json.dumps(pack["sourced_numbers"], ensure_ascii=False, default=str),
        derived_numbers="[]",
        model_inferred="[]",
        qa_passed=qa_passed,
        qa_violations=json.dumps(qa_violations or [], ensure_ascii=False),
        created_at=datetime.now(),
    )
    session.add(evidence)
    session.commit()
    session.refresh(evidence)
    return evidence
