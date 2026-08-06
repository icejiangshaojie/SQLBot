"""
AI2BI QA Checker — 全链路质检

三层质检：
1. SQL 级（已有 guardrail 增强）：表白名单、分区条件、只读校验、LIMIT
2. 结果级：行数检查、NULL 值检查、分区覆盖
3. 答案级：数值一致性、推导标注、口径完整性、禁止项检查

质检结果：
- passed=True: 正常展示，标记 ✅
- passed=False + violations: 展示结果但标注 ⚠️ 警告
- 严重违规（如大量无证据数字）：返回拦截建议
"""

import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── 结果级质检 ────────────────────────────────────

def check_result_quality(result: dict, sql: str) -> list[str]:
    """
    SQL 执行结果质检。

    检查项：
    - 结果是否为空
    - 关键指标列是否大量 NULL
    - 行数是否超限
    """
    violations = []
    data = result.get("data", [])
    fields = result.get("fields", [])

    # 空结果
    if not data:
        violations.append("SQL 查询结果为空，请检查查询条件")

    # 行数超限（安全阀值）
    if len(data) > 10000:
        violations.append(f"查询结果 {len(data)} 行，超过安全阈值 10000，可能影响性能")

    # NULL 值检查：对每列检查 NULL 比例
    if data and isinstance(data[0], dict):
        for field in fields[:10]:  # 只检查前 10 列
            null_count = sum(1 for row in data if row.get(field) is None or row.get(field) == "")
            null_ratio = null_count / len(data) if data else 0
            if null_ratio > 0.5:
                violations.append(f"列 '{field}' 的 NULL 值比例为 {null_ratio:.0%}，可能存在数据质量问题")

    return violations


# ── 答案级质检 ────────────────────────────────────

def check_evidence_consistency(answer_text: str, evidence_pack: dict) -> dict:
    """
    答案级质检：校验回答中的数字是否都有证据来源。

    返回:
        {
            "passed": bool,
            "violations": list[str],
            "sourced_count": int,
            "derived_count": int,
            "inferred_count": int,
            "unsourced_count": int,
        }
    """
    violations = []

    # 提取回答中所有数字
    answer_numbers = _extract_all_numbers(answer_text)

    # 从 Evidence Pack 获取已知数值
    sourced = set()
    for n in evidence_pack.get("sourced_numbers", []):
        val = n.get("value")
        if isinstance(val, (int, float)):
            sourced.add(round(float(val), 2))

    # 统计标签使用
    sql_tag_count = answer_text.count("[SQL]")
    calc_tag_count = answer_text.count("[计算")
    inferred_tag_count = answer_text.count("[模型推导]")

    # 检查无来源数字
    # 策略：如果数字附近有 [SQL] [计算] [模型推导] 标签，则视为已标注，不标记为无来源
    unsourced = []
    for num in answer_numbers:
        # 跳过非常小的数字（序号、标识等）
        if abs(num) < 2:
            continue
        # 检查是否在 [SQL] [计算] [模型推导] 标签附近
        if _is_near_tag(answer_text, num, ["[SQL]", "[计算", "[模型推导]"], window=80):
            continue
        # 也检查 sourced_numbers 中是否有近似匹配（聚合值可能与原始行值不同）
        rounded = round(num, 2)
        if _is_approximately_sourced(rounded, sourced):
            continue
        # 检查数字是否在 SQL 代码块内（不算无来源）
        if _is_in_sql_block(answer_text, num):
            continue
        unsourced.append(num)

    if unsourced:
        unsourced_str = ", ".join(str(n) for n in unsourced[:5])
        violations.append(f"回答中有 {len(unsourced)} 个数字无证据来源: {unsourced_str}...")

    # 检查口径完整性
    has_metric_def = "指标定义" in answer_text or "口径" in answer_text
    has_time_range = "时间" in answer_text or "范围" in answer_text or "pt" in answer_text.lower()
    has_sql_section = "```sql" in answer_text.lower() or "SQL" in answer_text

    if not has_metric_def:
        violations.append("回答缺少指标口径说明")
    if not has_sql_section and len(answer_numbers) > 0:
        violations.append("回答包含数据但未展示 SQL")

    # 检查禁止项：因果断言
    causal_patterns = [
        r"导致.*因为",
        r"因为.*所以.*下降",
        r"原因.*是.*导致",
    ]
    for pattern in causal_patterns:
        if re.search(pattern, answer_text):
            violations.append("回答中存在因果断言，需确认有业务规则支持")
            break

    # 检查禁止项：数值预测
    prediction_patterns = [
        r"预计.*将达到",
        r"预测.*约为",
        r"未来.*将达到",
    ]
    for pattern in prediction_patterns:
        if re.search(pattern, answer_text):
            violations.append("回答中存在数值预测，已违反禁止规则")
            break

    unsourced_count = len(unsourced)
    passed = unsourced_count == 0 and len(violations) <= 1

    return {
        "passed": passed,
        "violations": violations,
        "sourced_count": sql_tag_count,
        "derived_count": calc_tag_count,
        "inferred_count": inferred_tag_count,
        "unsourced_count": unsourced_count,
    }


def _extract_all_numbers(text: str) -> list[float]:
    """从文本中提取所有数字，过滤掉明显非数据数字（日期、月份、序号等）"""
    # 匹配：整数、小数、带千分位的数字
    pattern = re.compile(r'(?<![a-zA-Z_])(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.?\d*)(?![a-zA-Z_])')
    numbers = []
    for match in pattern.finditer(text):
        try:
            raw = match.group(0)
            val = float(raw.replace(",", ""))
            # 过滤掉明显非数据数字
            # - 年份（1900-2099）
            if 1900 <= val <= 2099 and "." not in raw:
                continue
            # - 月/日（1-31，不带小数）
            if 1 <= val <= 31 and "." not in raw and "," not in raw:
                # 检查上下文是否是日期
                start = max(0, match.start() - 5)
                end = min(len(text), match.end() + 5)
                context = text[start:end]
                if re.search(r'[月日号年/-]', context):
                    continue
            # - 百分比标签中的纯数字（如 "2位小数"）
            if val < 1 and "." not in raw:
                continue
            numbers.append(val)
        except (ValueError, TypeError):
            continue
    return numbers


def _is_near_tag(text: str, number: float, tags: list[str], window: int = 50) -> bool:
    """检查数字附近是否有标签（如 [SQL] 或 [模型推导]）"""
    # 尝试多种数字格式
    num_strs = [str(number)]
    if number == int(number):
        num_strs.append(f"{int(number):,}")  # 千分位
    else:
        num_strs.append(f"{number:.2f}")
        num_strs.append(f"{number:,.2f}")  # 千分位小数

    for num_str in num_strs:
        for tag in tags:
            for match in re.finditer(re.escape(num_str), text):
                start = max(0, match.start() - window)
                end = min(len(text), match.end() + window)
                context = text[start:end]
                if tag in context:
                    return True
    return False


def _is_approximately_sourced(value: float, sourced_set: set, tolerance: float = 0.01) -> bool:
    """检查值是否近似匹配已来源数值（允许微小精度差异）"""
    for s in sourced_set:
        if abs(value - s) / max(abs(s), 1) < tolerance:
            return True
    return False


def _is_in_sql_block(text: str, number: float) -> bool:
    """检查数字是否在 SQL 代码块内"""
    num_str = str(number)
    # 查找所有 ```sql ... ``` 块
    sql_blocks = re.findall(r'```sql.*?```', text, re.DOTALL | re.IGNORECASE)
    for block in sql_blocks:
        if num_str in block:
            return True
    return False


# ── 综合质检 ──────────────────────────────────────

def run_full_qa(
    sql: str,
    result: dict,
    answer_text: str,
    evidence_pack: dict,
) -> dict:
    """
    全链路质检入口。

    返回:
        {
            "passed": bool,
            "sql_violations": list[str],
            "result_violations": list[str],
            "answer_violations": list[str],
            "evidence_summary": dict,
        }
    """
    # 结果级质检
    result_violations = check_result_quality(result, sql)

    # 答案级质检
    answer_qa = check_evidence_consistency(answer_text, evidence_pack)

    all_violations = result_violations + answer_qa["violations"]
    passed = len(all_violations) == 0

    return {
        "passed": passed,
        "sql_violations": [],
        "result_violations": result_violations,
        "answer_violations": answer_qa["violations"],
        "evidence_summary": {
            "sourced_count": answer_qa["sourced_count"],
            "derived_count": answer_qa["derived_count"],
            "inferred_count": answer_qa["inferred_count"],
            "unsourced_count": answer_qa["unsourced_count"],
        },
    }
