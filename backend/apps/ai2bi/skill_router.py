"""
AI2BI Skill Router — Agent 优先路由，Skill 作为 Agent 内部知识加载。

路由流程：
1. 从 DB 查已发布的 Agent，按 entry_signals 匹配
2. 命中 Agent → 加载该 Agent 绑定的 Skills + 表 + 指标 + 隔离规则
3. 未命中 → 通用兜底（基座层 + 通用规则）
"""

import os
import re
import yaml
import logging
from pathlib import Path
from typing import Any
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

# AIBI_v2 知识库根目录（已并入 SQLBot/knowledge/AIBI_v2）
# skill_router.py 在 backend/apps/ai2bi/，需要往上 3 层到 SQLBot/ 再进 knowledge/AIBI_v2
AIBI_V2_ROOT = Path(os.environ.get(
    "AIBI_V2_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "knowledge", "AIBI_v2")
)).resolve()


# ── Cache ──

_skill_cache: dict[str, str] = {}


def load_skill_md(skill_path: str, force_reload: bool = False) -> str:
    """加载一个 SKILL.md 文件内容"""
    if not force_reload and skill_path in _skill_cache:
        return _skill_cache[skill_path]

    full_path = AIBI_V2_ROOT / "skills" / skill_path
    if not full_path.exists():
        return ""

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    _skill_cache[skill_path] = content
    return content


def clear_skill_cache(skill_path: str = None):
    """清除 Skill 缓存（保存文件后调用）"""
    if skill_path:
        _skill_cache.pop(skill_path, None)
    else:
        _skill_cache.clear()


def load_analysis_rules() -> str:
    """加载分析规则"""
    rules_path = AIBI_V2_ROOT / "data" / "analysis_rules.md"
    if rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def load_global_rules() -> str:
    """加载全局规则"""
    rules_path = AIBI_V2_ROOT / "data" / "global_rules.md"
    if rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def load_sql_rules() -> str:
    """加载 ODPS SQL 规则"""
    rules_path = AIBI_V2_ROOT / "data" / "sql_rules.md"
    if rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


# ── Agent Router ───────────────────────────────────

def route_question(question: str) -> dict[str, Any]:
    """
    Agent 优先路由。

    1. 从 DB 查已发布的 Agent
    2. 按 entry_signals 匹配
    3. 命中 → 加载 Agent 绑定的 Skills + 表 + 指标 + 隔离规则
    4. 未命中 → 通用兜底

    返回:
        {
            "agent": dict | None,        # 命中的 Agent
            "domain": str | None,        # 业务域
            "sub_skill": str | None,     # 子 Skill
            "confidence": float,
            "context_prompt": str,       # 注入到 LLM 的完整上下文
            "is_fallback": bool,         # 是否通用兜底
        }
    """
    question_lower = question.lower()

    # ── Step 1: 从 DB 查已发布的 Agent ──
    from apps.ai2bi.agent_models import Ai2biAgent
    from common.core.db import engine

    agents = []
    try:
        with Session(engine) as s:
            agents = s.exec(
                select(Ai2biAgent).where(Ai2biAgent.status == "published")
            ).all()
    except Exception as e:
        logger.warning(f"Failed to load agents from DB: {e}")

    # ── Step 2: 按 entry_signals 匹配 ──
    best_agent = None
    best_score = 0

    for agent in agents:
        signals = agent.entry_signals or []
        score = sum(1 for sig in signals if sig.lower() in question_lower)
        if score > best_score:
            best_score = score
            best_agent = agent

    # ── Step 3: 命中 Agent → 加载完整上下文 ──
    if best_agent and best_score > 0:
        return _build_agent_context(best_agent, question, best_score)

    # ── Step 4: 通用兜底 ──
    return _build_fallback_context(question)


def _build_agent_context(agent, question: str, score: int) -> dict[str, Any]:
    """构建命中 Agent 的上下文"""
    confidence = min(score / 2.0, 1.0)
    question_lower = question.lower()

    # 子 Skill 匹配（在 Agent 绑定的 Skills 内部路由）
    sub_skill = None
    sub_skill_keywords = {
        "card_trans": ["消费", "金额", "笔数", "mcc", "商户", "atm", "stockback", "回赠"],
        "mpau_analysis": ["mpau", "月活", "活跃", "沉默"],
        "ntb_analysis": ["ntb", "新户", "首刷", "开户", "转化"],
        "kpi_monitoring": ["kpi", "ytd", "mtd", "目标", "达成", "周报"],
        "card_partnership": ["商户活动", "品牌", "7-11", "麦当劳", "演唱会", "百万劲抽"],
    }

    best_sub = None
    best_sub_score = 0
    for skill_path in (agent.skills or []):
        skill_name = skill_path.split("/")[-1].replace("/SKILL.md", "").split("/")[-1]
        # Extract skill folder name
        parts = skill_path.split("/")
        if len(parts) >= 2:
            skill_id = parts[-2] if parts[-1] == "SKILL.md" else parts[-1].replace(".md", "")
        else:
            skill_id = skill_path.replace(".md", "")

        keywords = sub_skill_keywords.get(skill_id, [])
        sub_score = sum(1 for kw in keywords if kw in question_lower)
        if sub_score > best_sub_score:
            best_sub_score = sub_score
            best_sub = skill_path

    if best_sub:
        # Extract skill id from path
        parts = best_sub.split("/")
        sub_skill = parts[-2] if parts[-1] == "SKILL.md" else best_sub.replace(".md", "")

    # ── 构建上下文 prompt ──
    context_parts = []

    # 1. 全局规则
    global_rules = load_global_rules()
    if global_rules:
        context_parts.append(f"<global_rules>\n{global_rules}\n</global_rules>")

    # 2. ODPS SQL 规则
    sql_rules = load_sql_rules()
    if sql_rules:
        context_parts.append(f"<sql_rules>\n{sql_rules}\n</sql_rules>")

    # 3. Agent 信息
    context_parts.append(
        f"<agent name=\"{agent.name}\" vertical=\"{agent.vertical}\" version=\"{agent.version}\">\n"
        f"业务线: {agent.business_line}\n"
        f"描述: {agent.description or ''}\n"
        f"</agent>"
    )

    # 4. Agent 绑定的所有 Skills
    for skill_path in (agent.skills or []):
        skill_md = load_skill_md(skill_path)
        if skill_md:
            context_parts.append(f"<skill path=\"{skill_path}\">\n{skill_md}\n</skill>")

    # 5. 专属表白名单
    exclusive_tables = agent.exclusive_tables or []
    if exclusive_tables:
        table_list = "\n".join(f"  - {t}" for t in exclusive_tables)
        context_parts.append(f"<exclusive_tables>\n{table_list}\n</exclusive_tables>")

    # 6. 基座表（共享）
    shared_tables = agent.shared_tables or []
    if shared_tables:
        table_list = "\n".join(f"  - {t} (共享基座表)" for t in shared_tables)
        context_parts.append(f"<shared_tables>\n{table_list}\n</shared_tables>")

    # 7. 隔离规则
    if agent.isolation_rules:
        context_parts.append(f"<isolation_rules>\n{agent.isolation_rules}\n</isolation_rules>")

    # 8. 分析规则
    analysis_rules = load_analysis_rules()
    if analysis_rules:
        context_parts.append(f"<analysis_rules>\n{analysis_rules}\n</analysis_rules>")

    # 9. [新] 数据资产元数据（从 DB 加载）
    domain_assets = _load_domain_assets_from_db(agent.vertical)
    if domain_assets:
        context_parts.append(domain_assets)

    context_prompt = "\n\n".join(context_parts)

    return {
        "agent": {
            "id": agent.id,
            "code": agent.code,
            "name": agent.name,
            "vertical": agent.vertical,
        },
        "domain": agent.vertical,
        "sub_skill": sub_skill,
        "confidence": confidence,
        "context_prompt": context_prompt,
        "is_fallback": False,
        "exclusive_tables": exclusive_tables,
        "shared_tables": shared_tables,
        "capabilities": getattr(agent, 'capabilities', None) or ["data_query", "data_analysis"],
        "analysis_templates": getattr(agent, 'analysis_templates', None) or [],
    }


def _load_domain_assets_from_db(domain_code: str) -> str:
    """从数据库加载业务域的表字典、字段、指标、规则等元数据"""
    if not domain_code:
        return ""

    try:
        from sqlmodel import Session, select
        from common.core.db import engine
        from apps.ai2bi.asset_models import (
            Ai2biTableDict, Ai2biFieldDict, Ai2biMetricDict,
            Ai2biBusinessRule, Ai2biSqlTemplate
        )

        context_parts = []

        with Session(engine) as s:
            # 表字典
            tables = s.exec(
                select(Ai2biTableDict).where(
                    Ai2biTableDict.domain_code == domain_code,
                    Ai2biTableDict.is_active == True
                )
            ).all()
            if tables:
                table_lines = []
                for t in tables:
                    comment = t.table_comment or ""
                    table_lines.append(f"  - {t.table_name} ({comment})")
                context_parts.append(
                    f"<domain_tables domain=\"{domain_code}\">\n"
                    + "\n".join(table_lines)
                    + "\n</domain_tables>"
                )

            # 核心指标
            metrics = s.exec(
                select(Ai2biMetricDict).where(
                    Ai2biMetricDict.domain_code == domain_code,
                    Ai2biMetricDict.status.in_("confirmed", "candidate")
                )
            ).all()
            if metrics:
                metric_lines = []
                for m in metrics:
                    calc = m.calculation or ""
                    metric_lines.append(f"  - {m.cn_name}: {calc}")
                context_parts.append(
                    f"<domain_metrics domain=\"{domain_code}\">\n"
                    + "\n".join(metric_lines)
                    + "\n</domain_metrics>"
                )

            # 业务规则
            rules = s.exec(
                select(Ai2biBusinessRule).where(
                    Ai2biBusinessRule.domain_code == domain_code
                )
            ).all()
            if rules:
                rule_lines = []
                for r in rules:
                    rule_lines.append(f"  - [{r.severity or 'warning'}] {r.title}: {r.content}")
                    if r.example:
                        rule_lines.append(f"    示例: {r.example}")
                context_parts.append(
                    f"<domain_rules domain=\"{domain_code}\">\n"
                    + "\n".join(rule_lines)
                    + "\n</domain_rules>"
                )

            # SQL 模板
            templates = s.exec(
                select(Ai2biSqlTemplate).where(
                    Ai2biSqlTemplate.domain_code == domain_code
                )
            ).all()
            if templates:
                tpl_lines = []
                for t in templates:
                    tpl_lines.append(f"  - {t.name}: {t.sql_template[:100]}...")
                context_parts.append(
                    f"<domain_sql_templates domain=\"{domain_code}\">\n"
                    + "\n".join(tpl_lines)
                    + "\n</domain_sql_templates>"
                )

        return "\n\n".join(context_parts) if context_parts else ""

    except Exception as e:
        logger.warning(f"Failed to load domain assets for {domain_code}: {e}")
        return ""


def _build_fallback_context(question: str) -> dict[str, Any]:
    """通用兜底：未命中任何 Agent"""
    context_parts = []

    # 全局规则
    global_rules = load_global_rules()
    if global_rules:
        context_parts.append(f"<global_rules>\n{global_rules}\n</global_rules>")

    # SQL 规则
    sql_rules = load_sql_rules()
    if sql_rules:
        context_parts.append(f"<sql_rules>\n{sql_rules}\n</sql_rules>")

    # 通用兜底提示
    context_parts.append(
        "<fallback_mode>\n"
        "本次问题未命中任何业务 Agent，使用通用模式回答。\n"
        "注意：\n"
        "1. 只能使用用户已选择数据源中的表\n"
        "2. 遵守 ODPS 只读规则\n"
        "3. 如果不确定业务口径，在回答中说明\n"
        "</fallback_mode>"
    )

    context_prompt = "\n\n".join(context_parts)

    return {
        "agent": None,
        "domain": None,
        "sub_skill": None,
        "confidence": 0,
        "context_prompt": context_prompt,
        "is_fallback": True,
        "exclusive_tables": [],
        "shared_tables": [],
        "capabilities": ["data_query"],
        "analysis_templates": [],
    }


# ── 兼容旧接口 ─────────────────────────────────────

def get_skill_context_for_question(question: str) -> str:
    """
    便捷方法：返回要注入到 LLM prompt 的 Skill 上下文文本。
    现在走 Agent 路由，如果未命中 Agent 则返回通用兜底上下文。
    """
    result = route_question(question)
    return result.get("context_prompt", "")


# ── 指定 Skill 测试（开发态 override）─────────────

def get_explicit_skill_context(skill_path: str) -> dict[str, Any]:
    """
    开发态：强制加载指定 Skill，绕过 Agent 路由。

    用于 Skill 开发页的 @skill 测试对话。
    生产环境仍走 route_question() 的 Agent-first 路由。

    参数:
        skill_path: Skill 路径，如 "card/card_trans/SKILL.md"
                    也接受不带 skills/ 前缀的格式

    返回:
        与 route_question 相同结构的 dict
    """
    # 规范化路径：去掉 "skills/" 前缀
    if skill_path.startswith("skills/"):
        skill_path = skill_path[len("skills/"):]

    context_parts = []

    # 全局规则
    global_rules = load_global_rules()
    if global_rules:
        context_parts.append(f"<global_rules>\n{global_rules}\n</global_rules>")

    # SQL 规则
    sql_rules = load_sql_rules()
    if sql_rules:
        context_parts.append(f"<sql_rules>\n{sql_rules}\n</sql_rules>")

    # 分析规则
    analysis_rules = load_analysis_rules()
    if analysis_rules:
        context_parts.append(f"<analysis_rules>\n{analysis_rules}\n</analysis_rules>")

    # 指定 Skill（force_reload 确保读取最新内容）
    skill_md = load_skill_md(skill_path, force_reload=True)
    if skill_md:
        context_parts.append(
            f"<skill path=\"{skill_path}\" mode=\"explicit_test\">\n{skill_md}\n</skill>"
        )
    else:
        context_parts.append(f"<error>Skill not found: {skill_path}</error>")

    context_parts.append(
        "<explicit_test_mode>\n"
        "当前为指定 Skill 测试模式，已绕过 Agent 自动路由。\n\n"
        "重要：在此模式下，你的工作边界已扩展，不再仅限于生成 SQL。你可以：\n"
        "1. 回答关于 Skill 内容的问题（涉及表、约束、输出格式、业务规则等）\n"
        "2. 生成 SQL 查询数据\n"
        "3. 基于查询结果进行分析\n\n"
        "当用户询问 Skill 内容、业务规则、指标定义等知识性问题时，你必须基于上述 Skill 原文回答，而不是拒绝。\n\n"
        "输出格式规则（覆盖基座规则）：\n"
        "- 如果是知识问答（不需要生成 SQL），返回：{\"success\":true,\"sql\":\"-- knowledge_qa\",\"knowledge_answer\":\"你的回答内容\",\"tables\":[],\"chart-type\":\"table\"}\n"
        "- 如果需要生成 SQL 查询数据，仍按正常格式返回：{\"success\":true,\"sql\":\"SELECT ...\",\"tables\":[...],\"chart-type\":\"...\"}\n"
        "- 绝对不要返回 {\"success\":false} 来拒绝知识性问题\n"
        "</explicit_test_mode>"
    )

    context_prompt = "\n\n".join(context_parts)

    return {
        "agent": None,
        "domain": None,
        "sub_skill": skill_path,
        "confidence": 1.0,
        "context_prompt": context_prompt,
        "is_fallback": False,
        "is_explicit_skill": True,
        "exclusive_tables": [],
        "shared_tables": [],
        "capabilities": ["knowledge_qa", "data_query", "data_analysis"],
        "analysis_templates": [],
    }
