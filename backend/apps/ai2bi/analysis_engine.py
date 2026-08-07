"""
AI2BI Phase 0 确定性基础分析引擎 — 单查询结果集的可复现计算。

职责：
1. 接收一条已执行 SQL 的标准化结果 {fields, data}，输出 AnalysisFact 列表。
2. 只做可复现计算，不调用数据库、不调用 LLM、不编造数据。
3. 无法确认列角色或计算前提时，输出 status=data_insufficient 的事实，并给出原因。

Phase 0 仅支持单结果集算子：
- direct：SQL 直出值（单行聚合或指定行/列）。
- summary：数值列 count/sum/mean/min/max。
- trend：识别时间字段且至少两个有效点时，计算首末差异、方向、峰值、谷值、波动。
- ranking/structure：识别一个维度列与一个数值列时，计算 Top/Bottom N、Top N 合计及占比。
- comparison：结果明确包含两条可比较周期记录时，计算差值与增长率。
- anomaly：对满足最小样本量的连续数值序列运行 IQR 规则；否则不可判定。

所有算子统一处理：NULL、字符串数值、零分母、重复维度、不可排序时间、货币/百分比显示精度和空结果。
"""

from __future__ import annotations

import re
from typing import Any

from .analysis_contract import AnalysisFact, FactSource, FactStatus

# 时间字段名启发式（出现在列名中的关键词）
_TIME_HINTS = ("date", "dt", "day", "month", "time", "ym", "日期", "时间", "月份", "日")
# 维度字段名启发式
_DIM_HINTS = ("name", "code", "id", "cust", "customer", "channel", "segment", "type", "category",
              "客户", "渠道", "客群", "分行", "商户")
# 排除的"维度"列（可能是数值主键/金额列的误判）
_DIM_EXCLUDE = ("amt", "amount", "bal", "balance", "count", "num", "prin", "inter", "金额", "余额", "笔数")


def analyze_result(result: dict[str, Any], _metric_context: list | None = None) -> list[AnalysisFact]:
    """对单条结果集执行确定性分析，返回事实列表。"""
    fields = result.get("fields") or []
    rows = result.get("data") or []

    facts: list[AnalysisFact] = []

    if not rows:
        facts.append(_fact(
            "data_empty", "data_insufficient", "查询结果为空",
            status=FactStatus.DATA_INSUFFICIENT, reason="SQL 未返回任何行，无法分析。",
        ))
        return facts

    if not fields:
        facts.append(_fact(
            "no_fields", "data_insufficient", "结果缺少字段定义",
            status=FactStatus.DATA_INSUFFICIENT, reason="结果集未提供字段列表，无法识别列角色。",
        ))
        return facts

    numeric_cols = _numeric_columns(fields, rows)
    time_col = _time_column(fields)
    dim_col = _dimension_column(fields, numeric_cols)

    # 1. 直出事实：单行时，每个数值列直出
    if len(rows) == 1:
        _add_direct_facts(facts, fields, rows[0])
    else:
        _add_summary_facts(facts, fields, rows, numeric_cols)

    # 2. 趋势：有明确时间列且至少两个有效点
    if time_col:
        _add_trend_facts(facts, rows, time_col, numeric_cols)

    # 3. 排名与结构：有维度列 + 数值列
    if dim_col and numeric_cols:
        _add_ranking_facts(facts, rows, dim_col, numeric_cols)

    # 4. 双周期比较：仅在能识别两条可比较记录时
    _add_comparison_facts(facts, rows, time_col, numeric_cols)

    # 5. 规则型异常：对时间序列数值列执行 IQR
    if time_col and numeric_cols:
        _add_anomaly_facts(facts, rows, time_col, numeric_cols[0])

    # 6. 完全没有可识别数值时，给出数据不足提示
    if not facts:
        facts.append(_fact(
            "no_analyzable", "data_insufficient", "无法识别可用于分析的数值",
            status=FactStatus.DATA_INSUFFICIENT,
            reason="结果集中没有可识别的数值列，或无法确认列角色。",
        ))

    return facts


def _fact(fact_id: str, category: str, label: str, value: float | None = None,
          unit: str | None = None, **kw) -> AnalysisFact:
    return AnalysisFact(fact_id=fact_id, category=category, label=label, value=value, unit=unit, **kw)


def _to_number(val: Any) -> float | None:
    """宽容解析数值，处理字符串带千分位/货币/百分号；无法解析返回 None。"""
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.replace(",", "").replace("，", "").replace(" ", "").replace("%", "")
        s = re.sub(r"[HKD$¥€£元]", "", s, flags=re.IGNORECASE)
        try:
            return float(s)
        except (ValueError, TypeError):
            return None
    return None


def _numeric_columns(fields: list, rows: list) -> list[str]:
    """识别数值列：字段 value 为数值，或首行可解析为数值（排除时间/纯维度）。"""
    candidates = []
    for f in fields:
        fname = str(f)
        if any(h in fname.lower() for h in _TIME_HINTS):
            continue
        # 采样前几行判断是否数值
        sample = [_to_number(r.get(f)) if isinstance(r, dict) else None for r in rows[:5]]
        numeric = any(v is not None for v in sample)
        if numeric:
            candidates.append(f)
    return candidates


def _time_column(fields: list) -> str | None:
    for f in fields:
        fname = str(f).lower()
        if any(h in fname for h in _TIME_HINTS):
            return str(f)
    return None


def _dimension_column(fields: list, numeric_cols: list[str]) -> str | None:
    for f in fields:
        fname = str(f)
        fl = fname.lower()
        if f in numeric_cols:
            continue
        if any(h in fname for h in _DIM_HINTS) and not any(x in fl for x in _DIM_EXCLUDE):
            return fname
    return None


def _add_direct_facts(facts: list, fields: list, row: dict) -> None:
    for f in fields:
        val = _to_number(row.get(f))
        if val is not None:
            facts.append(_fact(
                f"direct_{_safe_id(f)}", "summary", f"直出值 {f}: {val}",
                value=val, column=str(f), source_type=FactSource.SQL,
                display=_fmt(val), row_refs=["row[0]"],
            ))


def _add_summary_facts(facts: list, _fields: list, rows: list, numeric_cols: list[str]) -> None:
    for col in numeric_cols:
        values = [_to_number(r.get(col)) if isinstance(r, dict) else None for r in rows]
        valid = [v for v in values if v is not None]
        if not valid:
            continue
        total = sum(valid)
        avg = total / len(valid)
        facts.append(_fact(
            f"sum_{_safe_id(col)}", "summary", f"{col} 合计",
            value=total, unit="", column=col, source_type=FactSource.SQL,
            display=_fmt(total), row_refs=[f"row[0..{len(valid) - 1}]"],
        ))
        facts.append(_fact(
            f"avg_{_safe_id(col)}", "summary", f"{col} 均值",
            value=avg, unit="", column=col, source_type=FactSource.BACKEND,
            formula=f"sum({col}) / count",
            input_refs=[f"sum_{_safe_id(col)}"],
            display=_fmt(avg),
        ))


def _add_trend_facts(facts: list, rows: list, time_col: str, numeric_cols: list[str]) -> None:
    ordered = _ordered_by_time(rows, time_col)
    if len(ordered) < 2:
        return
    series = [
        (i, _to_number(r.get(numeric_cols[0])) if isinstance(r, dict) else None)
        for i, r in enumerate(ordered)
    ]
    valid = [v for _, v in series if v is not None]
    if len(valid) < 2:
        return
    first_val = valid[0]
    last_val = valid[-1]
    diff = last_val - first_val
    direction = "上升" if diff > 0 else ("下降" if diff < 0 else "持平")
    facts.append(_fact(
        "trend_direction", "trend", f"趋势方向: {direction}",
        value=diff, unit="", source_type=FactSource.BACKEND,
        formula="last - first",
        input_refs=[f"direct_{_safe_id(numeric_cols[0])}"],
        display=f"{direction}（首末差值 {_fmt(diff)}）",
    ))
    peak = max(valid)
    trough = min(valid)
    facts.append(_fact(
        "trend_peak", "trend", f"峰值: {_fmt(peak)}",
        value=peak, unit="", source_type=FactSource.SQL,
        display=_fmt(peak),
    ))
    facts.append(_fact(
        "trend_trough", "trend", f"谷值: {_fmt(trough)}",
        value=trough, unit="", source_type=FactSource.SQL,
        display=_fmt(trough),
    ))


def _add_ranking_facts(facts: list, rows: list, dim_col: str, numeric_cols: list[str]) -> None:
    col = numeric_cols[0]
    by_dim: dict[str, float] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        dim_val = str(r.get(dim_col))
        val = _to_number(r.get(col))
        if val is None:
            continue
        by_dim[dim_val] = by_dim.get(dim_val, 0.0) + val
    if not by_dim:
        return
    ranked = sorted(by_dim.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(v for _, v in ranked)
    if total <= 0:
        return
    top_n = ranked[:5]
    top_sum = sum(v for _, v in top_n)
    top_share = top_sum / total
    facts.append(_fact(
        "top5_share", "structure", "Top 5 集中度",
        value=top_share, unit="ratio", source_type=FactSource.BACKEND,
        formula="sum(top5) / total",
        input_refs=[f"top5_total_{_safe_id(col)}", f"sum_{_safe_id(col)}"],
        display=f"{top_share:.1%}",
    ))
    for rank, (name, v) in enumerate(top_n, start=1):
        facts.append(_fact(
            f"rank_{_safe_id(col)}_{rank}", "ranking", f"Top {rank}: {name}",
            value=v, unit="", column=col, source_type=FactSource.SQL,
            display=f"{name}={_fmt(v)}",
        ))


def _add_comparison_facts(facts: list, rows: list, time_col: str | None, numeric_cols: list[str]) -> None:
    """仅在明确两条可比较记录时计算差值与增长率。"""
    if len(numeric_cols) == 0 or len(rows) < 2:
        return
    col = numeric_cols[0]
    # 若结果就是两行（如两期聚合），直接比较
    if len(rows) == 2:
        a = _to_number(rows[0].get(col)) if isinstance(rows[0], dict) else None
        b = _to_number(rows[1].get(col)) if isinstance(rows[1], dict) else None
        if a is not None and b is not None:
            _append_delta(facts, a, b, col)
        return
    # 有明确时间列时，比较首末
    if time_col:
        ordered = _ordered_by_time(rows, time_col)
        if len(ordered) >= 2:
            a = _to_number(ordered[0].get(col)) if isinstance(ordered[0], dict) else None
            b = _to_number(ordered[-1].get(col)) if isinstance(ordered[-1], dict) else None
            if a is not None and b is not None:
                _append_delta(facts, a, b, col)


def _append_delta(facts: list, a: float, b: float, col: str) -> None:
    diff = b - a
    facts.append(_fact(
        f"delta_{_safe_id(col)}", "comparison", f"{col} 差值",
        value=diff, unit="", source_type=FactSource.BACKEND,
        formula="later - earlier",
        display=f"差值 {_fmt(diff)}",
    ))
    if a == 0:
        facts.append(_fact(
            f"growth_{_safe_id(col)}", "comparison", f"{col} 增长率",
            status=FactStatus.DATA_INSUFFICIENT,
            reason="基期值为 0，无法计算增长率。",
        ))
    else:
        growth = diff / a
        facts.append(_fact(
            f"growth_{_safe_id(col)}", "comparison", f"{col} 增长率",
            value=growth, unit="ratio", source_type=FactSource.BACKEND,
            formula="(later - earlier) / earlier",
            display=f"{growth:.1%}",
        ))


def _add_anomaly_facts(facts: list, rows: list, time_col: str, col: str) -> None:
    ordered = _ordered_by_time(rows, time_col)
    values = [(_to_number(r.get(col)) if isinstance(r, dict) else None) for r in ordered]
    valid = [v for v in values if v is not None]
    if len(valid) < 8:  # 最小样本量
        facts.append(_fact(
            "anomaly_iqr", "anomaly", "异常点检测",
            status=FactStatus.DATA_INSUFFICIENT,
            reason="样本量不足（需至少 8 个时间点），无法进行 IQR 异常检测。",
        ))
        return
    q1, q3 = _quartiles(valid)
    iqr = q3 - q1
    if iqr is None or iqr == 0:
        facts.append(_fact(
            "anomaly_iqr", "anomaly", "异常点检测",
            status=FactStatus.DATA_INSUFFICIENT,
            reason="数值波动为零或 IQR 无法计算，未检测到异常。",
        ))
        return
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    anomalies = [v for v in valid if v < lower or v > upper]
    if anomalies:
        facts.append(_fact(
            "anomaly_iqr", "anomaly", f"检测到 {len(anomalies)} 个异常值",
            value=float(len(anomalies)), unit="个", source_type=FactSource.BACKEND,
            formula="IQR 规则: < Q1-1.5*IQR 或 > Q3+1.5*IQR",
            display=f"{len(anomalies)} 个异常点",
        ))
    else:
        facts.append(_fact(
            "anomaly_iqr", "anomaly", "未检测到异常点",
            value=0.0, unit="个", source_type=FactSource.BACKEND,
            display="无异常点",
        ))


def _ordered_by_time(rows: list, time_col: str) -> list:
    """按时间列排序；无法排序时返回原始顺序。"""
    def _key(r):
        if not isinstance(r, dict):
            return (0, 0)
        v = r.get(time_col)
        if v is None:
            return (1, 0)
        return (0, str(v))
    try:
        return sorted(rows, key=_key)
    except Exception:
        return rows


def _quartiles(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    s = sorted(values)
    n = len(s)
    def _pct(p):
        idx = (n - 1) * p
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return s[lo] * (1 - frac) + s[hi] * frac
    return _pct(0.25), _pct(0.75)


def _fmt(v: float) -> str:
    """简洁显示：绝对值大时用千分位，否则保留两位小数。"""
    if abs(v) >= 10000:
        return f"{v:,.2f}"
    return f"{v:.2f}"


def _safe_id(name: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", str(name)) or "col"
