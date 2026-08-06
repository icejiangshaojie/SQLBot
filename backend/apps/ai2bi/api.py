"""AI2BI API routes: metrics, memory, skill-dev files, agents."""
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, Body, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from common.core.db import engine
from common.core.config import settings
import os, json, yaml

from apps.ai2bi.models import (
    Ai2biMetricDomain, Ai2biMetric, Ai2biMetricHistory,
    Ai2biMemory, Ai2biMemorySummary,
)
from apps.ai2bi.asset_models import (
    Ai2biTableDict, Ai2biFieldDict, Ai2biMetricDict,
    Ai2biBusinessRule, Ai2biSqlTemplate, Ai2biTableLineage,
)
from apps.ai2bi.agent_models import (
    Ai2biAgent, Ai2biAgentGrant, Ai2biAgentRequest, Ai2biAgentVersion,
)

router = APIRouter(tags=["ai2bi"], prefix="/ai2bi", include_in_schema=False)

AIBI_V2_ROOT = Path(os.environ.get(
    "AIBI_V2_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "AIBI_v2")
)).resolve()

def _session():
    return Session(engine)


# ═══ 指标管理 ═══════════════════════════════════════

class MetricDomainCreate(BaseModel):
    code: str
    cn_name: str
    description: Optional[str] = None
    owner: Optional[str] = None

class MetricCreate(BaseModel):
    domain_id: int
    cn_name: str
    en_name: Optional[str] = None
    tier: str = "L2"
    business_definition: Optional[str] = None
    calculation: Optional[str] = None
    mandatory_rules: Optional[str] = None
    sql_template: Optional[str] = None
    grain: Optional[str] = None
    source_tables: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None

class MetricUpdate(BaseModel):
    cn_name: Optional[str] = None
    en_name: Optional[str] = None
    tier: Optional[str] = None
    business_definition: Optional[str] = None
    calculation: Optional[str] = None
    mandatory_rules: Optional[str] = None
    sql_template: Optional[str] = None
    grain: Optional[str] = None
    source_tables: Optional[str] = None
    notes: Optional[str] = None


@router.get("/metrics/domains")
async def list_metric_domains():
    with _session() as s:
        domains = s.exec(select(Ai2biMetricDomain).order_by(Ai2biMetricDomain.sort_order)).all()
        return domains

@router.post("/metrics/domains")
async def create_metric_domain(body: MetricDomainCreate):
    with _session() as s:
        domain = Ai2biMetricDomain(**body.dict())
        s.add(domain); s.commit(); s.refresh(domain)
        return domain

@router.get("/metrics/list/{domain_id}")
async def list_metrics(domain_id: int, include_deleted: bool = False):
    with _session() as s:
        stmt = select(Ai2biMetric).where(Ai2biMetric.domain_id == domain_id)
        if not include_deleted:
            stmt = stmt.where(Ai2biMetric.status != "deleted")
        stmt = stmt.order_by(Ai2biMetric.tier, Ai2biMetric.cn_name)
        return s.exec(stmt).all()

@router.post("/metrics/create")
async def create_metric(body: MetricCreate):
    with _session() as s:
        m = Ai2biMetric(**body.dict(), status="candidate", version=1,
                         created_at=datetime.now(), updated_at=datetime.now())
        s.add(m); s.commit(); s.refresh(m)
        return m

@router.put("/metrics/update/{metric_id}")
async def update_metric(metric_id: int, body: MetricUpdate):
    with _session() as s:
        m = s.get(Ai2biMetric, metric_id)
        if not m: raise HTTPException(404, "Metric not found")
        # Save history
        import json
        snapshot = json.dumps({k: getattr(m, k) for k in dir(m) if not k.startswith('_') and not callable(getattr(m, k))}, default=str, ensure_ascii=False)
        s.add(Ai2biMetricHistory(metric_id=m.id, version=m.version, snapshot=snapshot,
                                  changed_at=datetime.now()))
        for k, v in body.dict(exclude_unset=True).items():
            setattr(m, k, v)
        m.version += 1
        m.updated_at = datetime.now()
        s.add(m); s.commit(); s.refresh(m)
        return m

@router.post("/metrics/confirm/{metric_id}")
async def confirm_metric(metric_id: int):
    with _session() as s:
        m = s.get(Ai2biMetric, metric_id)
        if not m: raise HTTPException(404, "Metric not found")
        m.status = "confirmed"
        m.updated_at = datetime.now()
        s.add(m); s.commit()
        return {"status": "confirmed"}

@router.delete("/metrics/delete/{metric_id}")
async def delete_metric(metric_id: int):
    with _session() as s:
        m = s.get(Ai2biMetric, metric_id)
        if not m: raise HTTPException(404, "Metric not found")
        m.status = "deleted"
        m.updated_at = datetime.now()
        s.add(m); s.commit()
        return {"status": "deleted"}

@router.get("/metrics/history/{metric_id}")
async def metric_history(metric_id: int):
    with _session() as s:
        return s.exec(select(Ai2biMetricHistory)
                       .where(Ai2biMetricHistory.metric_id == metric_id)
                       .order_by(Ai2biMetricHistory.version.desc())).all()


# ═══ 我的记忆 ═══════════════════════════════════════

class MemoryCreate(BaseModel):
    scope: str = "user"
    category: Optional[str] = None
    content: str
    pinned: bool = False

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    pinned: Optional[bool] = None
    category: Optional[str] = None


@router.get("/memory")
async def list_memory(user_id: int = 1):
    with _session() as s:
        return s.exec(select(Ai2biMemory)
                       .where(Ai2biMemory.user_id == user_id, Ai2biMemory.status == "active")
                       .order_by(Ai2biMemory.pinned.desc(), Ai2biMemory.created_at.desc())).all()

@router.post("/memory")
async def create_memory(body: MemoryCreate, user_id: int = 1):
    with _session() as s:
        m = Ai2biMemory(**body.dict(), user_id=user_id,
                         created_at=datetime.now(), updated_at=datetime.now())
        s.add(m); s.commit(); s.refresh(m)
        return m

@router.put("/memory/{memory_id}")
async def update_memory(memory_id: int, body: MemoryUpdate):
    with _session() as s:
        m = s.get(Ai2biMemory, memory_id)
        if not m: raise HTTPException(404, "Memory not found")
        for k, v in body.dict(exclude_unset=True).items():
            setattr(m, k, v)
        m.updated_at = datetime.now()
        s.add(m); s.commit(); s.refresh(m)
        return m

@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: int):
    with _session() as s:
        m = s.get(Ai2biMemory, memory_id)
        if not m: raise HTTPException(404, "Memory not found")
        m.status = "deleted"
        m.updated_at = datetime.now()
        s.add(m); s.commit()
        return {"status": "deleted"}

@router.get("/memory/summaries")
async def list_memory_summaries(user_id: int = 1):
    with _session() as s:
        return s.exec(select(Ai2biMemorySummary)
                       .where(Ai2biMemorySummary.user_id == user_id)
                       .order_by(Ai2biMemorySummary.created_at.desc())).all()


# ═══ Skill 开发中心 — 文件树 ═══════════════════════

ALLOWED_DIRS = {"CLAUDE.md", "data", "domain", "skills"}


def _build_tree(root: Path, rel: str = "") -> list[dict]:
    """Build a file tree from AIBI_v2 root, only showing allowed dirs."""
    items = []
    base = root / rel if rel else root
    if not base.exists():
        return items
    for entry in sorted(base.iterdir()):
        name = entry.name
        if rel == "" and name not in ALLOWED_DIRS:
            continue
        path = f"{rel}/{name}" if rel else name
        if entry.is_dir():
            children = _build_tree(root, path)
            if children:
                items.append({"name": name, "path": path, "type": "dir", "children": children})
        elif entry.is_file() and name.endswith((".md", ".yaml", ".yml")):
            items.append({"name": name, "path": path, "type": "file"})
    return items


@router.get("/skill-dev/files")
async def list_skill_files():
    return _build_tree(AIBI_V2_ROOT)

@router.get("/skill-dev/files/content")
async def get_file_content(path: str):
    full = (AIBI_V2_ROOT / path).resolve()
    if not str(full).startswith(str(AIBI_V2_ROOT)):
        raise HTTPException(403, "Access denied")
    if not full.exists() or not full.is_file():
        raise HTTPException(404, "File not found")
    return {"path": path, "content": full.read_text(encoding="utf-8")}

@router.post("/skill-dev/files/content")
async def save_file_content(path: str = Body(...), content: str = Body(...)):
    full = (AIBI_V2_ROOT / path).resolve()
    if not str(full).startswith(str(AIBI_V2_ROOT)):
        raise HTTPException(403, "Access denied")
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    # 清除 Skill 缓存，确保测试对话读取最新内容
    try:
        from apps.ai2bi.skill_router import clear_skill_cache
        if path.startswith("skills/"):
            skill_rel = path[len("skills/"):]
            clear_skill_cache(skill_rel)
        else:
            clear_skill_cache()
    except Exception:
        pass
    return {"status": "saved", "path": path}

@router.post("/skill-dev/scaffold")
async def scaffold_skill(name: str = Body(...)):
    skill_dir = AIBI_V2_ROOT / "skills" / name
    if skill_dir.exists():
        raise HTTPException(400, f"Skill '{name}' already exists")
    skill_dir.mkdir(parents=True)
    sk = skill_dir / "SKILL.md"
    sk.write_text(f"""# {name}

> 定位：[描述这个 Skill 处理什么问题]
> 版本：v1.0 | {datetime.now().strftime('%Y-%m-%d')}

---

## 一、Skill 定义

```yaml
skill_id: {name}
skill_name: [中文名]
version: "1.0"
layer: L2_scenario
triggered_by:
  - [触发关键词]
```

## 二、执行原则
## 三、执行 SOP
## 四、输入参数
## 五、输出规范
## 六、功能边界
## 七、版本记录
""", encoding="utf-8")
    return {"status": "created", "name": name, "open": f"skills/{name}/SKILL.md"}


# ═══ 数据资产：术语/训练/规则（AI2BI 原生接口）════════════════════

from sqlalchemy import text as _text

@router.get("/assets/terminology")
async def assets_terminology():
    """术语列表"""
    with _session() as s:
        rows = s.execute(_text(
            "SELECT id, word, description FROM terminology WHERE enabled = true ORDER BY word"
        )).fetchall()
        return [{"id": r[0], "word": r[1], "description": r[2]} for r in rows]

@router.get("/assets/training")
async def assets_training():
    """SQL 样例列表"""
    with _session() as s:
        rows = s.execute(_text(
            "SELECT id, question, description FROM data_training WHERE enabled = true ORDER BY id"
        )).fetchall()
        return [{"id": r[0], "question": r[1], "description": r[2]} for r in rows]

@router.get("/assets/rules")
async def assets_rules():
    """硬规则"""
    with _session() as s:
        rows = s.execute(_text(
            "SELECT id, name, prompt FROM custom_prompt WHERE name = '卡域分析硬规则'"
        )).fetchall()
        if rows:
            return {"name": rows[0][1], "prompt": rows[0][2]}
        return {"name": "", "prompt": ""}


# ═══ 表管理：从 CoreTable/CoreField 读 ODPS 白名单表 ════════════

@router.get("/tables/list")
async def tables_list():
    """ODPS 白名单表列表"""
    with _session() as s:
        from apps.datasource.models.datasource import CoreTable, CoreField
        tables = s.exec(select(CoreTable).where(CoreTable.ds_id == 3)).all()
        result = []
        for t in tables:
            field_count = len(s.exec(select(CoreField).where(CoreField.table_id == t.id)).all())
            result.append({
                "id": t.id,
                "table_name": t.table_name,
                "table_comment": t.table_comment or "",
                "fields": field_count,
                "layer": _guess_layer(t.table_name),
            })
        return result

@router.get("/tables/{table_id}/fields")
async def table_fields(table_id: int):
    """表字段列表"""
    with _session() as s:
        from apps.datasource.models.datasource import CoreField
        fields = s.exec(select(CoreField).where(CoreField.table_id == table_id).order_by(CoreField.field_index)).all()
        return [{"field_name": f.field_name, "field_type": f.field_type, "field_comment": f.field_comment} for f in fields]

@router.post("/tables/{table_name}/sync")
async def sync_table_fields(table_name: str):
    """从 ODPS 同步表字段到 CoreField"""
    from apps.db.db import get_fields
    from apps.datasource.models.datasource import CoreDatasource, CoreTable, CoreField
    with _session() as s:
        ds = s.get(CoreDatasource, 3)
        # Find or create CoreTable
        t = s.exec(select(CoreTable).where(CoreTable.ds_id == 3, CoreTable.table_name == table_name)).first()
        if not t:
            t = CoreTable(ds_id=3, table_name=table_name, table_comment="", checked=True)
            s.add(t); s.commit(); s.refresh(t)
        # Delete old fields
        old = s.exec(select(CoreField).where(CoreField.table_id == t.id)).all()
        for f in old:
            s.delete(f)
        s.commit()
        # Get fields from ODPS
        fields = get_fields(ds, table_name)
        for i, f in enumerate(fields):
            s.add(CoreField(ds_id=3, table_id=t.id, field_name=f.fieldName,
                           field_type=f.fieldType, field_comment=f.fieldComment,
                           checked=True, field_index=i))
        s.commit()
        return {"table": table_name, "fields_synced": len(fields)}


# ═══ Agent 管理 ═══════════════════════════════════════

class AgentCreate(BaseModel):
    code: str
    name: str
    vertical: str
    description: Optional[str] = None
    business_line: str = "零售"
    entry_signals: list[str] = []
    skills: list[str] = []
    exclusive_tables: list[str] = []
    shared_tables: list[str] = []
    isolation_rules: Optional[str] = None
    capabilities: Optional[list[str]] = None
    analysis_templates: Optional[list[str]] = None
    test_case_path: Optional[str] = None
    qa_config: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entry_signals: Optional[list[str]] = None
    skills: Optional[list[str]] = None
    exclusive_tables: Optional[list[str]] = None
    shared_tables: Optional[list[str]] = None
    isolation_rules: Optional[str] = None
    capabilities: Optional[list[str]] = None
    analysis_templates: Optional[list[str]] = None
    test_case_path: Optional[str] = None
    qa_config: Optional[str] = None


@router.get("/agents")
async def list_agents():
    """所有 Agent 列表"""
    with _session() as s:
        agents = s.exec(select(Ai2biAgent).order_by(Ai2biAgent.id)).all()
        result = []
        for a in agents:
            # Count grants
            grant_count = len(s.exec(select(Ai2biAgentGrant).where(
                Ai2biAgentGrant.agent_id == a.id, Ai2biAgentGrant.status == "active")).all())
            result.append({
                "id": a.id, "code": a.code, "name": a.name,
                "vertical": a.vertical, "description": a.description,
                "status": a.status, "version": a.version,
                "business_line": a.business_line, "owner": a.owner,
                "entry_signals": a.entry_signals or [],
                "skills": a.skills or [],
                "exclusive_tables": a.exclusive_tables or [],
                "shared_tables": a.shared_tables or [],
                "capabilities": a.capabilities or ["data_query"],
                "analysis_templates": a.analysis_templates or [],
                "test_case_path": a.test_case_path or "",
                "grant_count": grant_count,
                "skill_count": len(a.skills or []),
                "table_count": len(a.exclusive_tables or []),
            })
        return result

@router.post("/agents")
async def create_agent(body: AgentCreate):
    with _session() as s:
        existing = s.exec(select(Ai2biAgent).where(Ai2biAgent.code == body.code)).first()
        if existing:
            raise HTTPException(400, f"Agent '{body.code}' already exists")
        a = Ai2biAgent(**body.dict(), status="dev", version="0.1",
                        created_at=datetime.now(), updated_at=datetime.now())
        s.add(a); s.commit(); s.refresh(a)
        # Auto-grant owner
        s.add(Ai2biAgentGrant(agent_id=a.id, user_id=1, grant_type="owner",
                               created_at=datetime.now()))
        s.commit()
        return {"id": a.id, "code": a.code, "status": "created"}

@router.get("/agents/{agent_id}")
async def get_agent(agent_id: int):
    with _session() as s:
        a = s.get(Ai2biAgent, agent_id)
        if not a: raise HTTPException(404, "Agent not found")
        grants = s.exec(select(Ai2biAgentGrant).where(
            Ai2biAgentGrant.agent_id == agent_id, Ai2biAgentGrant.status == "active")).all()
        versions = s.exec(select(Ai2biAgentVersion).where(
            Ai2biAgentVersion.agent_id == agent_id).order_by(Ai2biAgentVersion.published_at.desc())).all()
        return {
            "id": a.id, "code": a.code, "name": a.name,
            "vertical": a.vertical, "description": a.description,
            "status": a.status, "version": a.version,
            "business_line": a.business_line, "owner": a.owner,
            "entry_signals": a.entry_signals or [],
            "skills": a.skills or [],
            "exclusive_tables": a.exclusive_tables or [],
            "shared_tables": a.shared_tables or [],
            "metric_ids": a.metric_ids or [],
            "isolation_rules": a.isolation_rules or "",
            "capabilities": a.capabilities or ["data_query"],
            "analysis_templates": a.analysis_templates or [],
            "test_case_path": a.test_case_path or "",
            "qa_config": a.qa_config or "",
            "grants": [{"user_id": g.user_id, "type": g.grant_type} for g in grants],
            "versions": [{"version": v.version, "changelog": v.changelog,
                          "published_at": str(v.published_at)} for v in versions],
        }

@router.put("/agents/{agent_id}")
async def update_agent(agent_id: int, body: AgentUpdate):
    with _session() as s:
        a = s.get(Ai2biAgent, agent_id)
        if not a: raise HTTPException(404, "Agent not found")
        for k, v in body.dict(exclude_unset=True).items():
            setattr(a, k, v)
        a.updated_at = datetime.now()
        s.add(a); s.commit()
        return {"status": "updated"}

@router.post("/agents/{agent_id}/publish")
async def publish_agent(agent_id: int, changelog: str = Body("", embed=True)):
    """发布 Agent：保存版本快照，状态改为 published"""
    import json as _json
    with _session() as s:
        a = s.get(Ai2biAgent, agent_id)
        if not a: raise HTTPException(404, "Agent not found")
        # Save version snapshot
        snapshot = _json.dumps({
            "code": a.code, "name": a.name, "skills": a.skills,
            "exclusive_tables": a.exclusive_tables, "shared_tables": a.shared_tables,
            "entry_signals": a.entry_signals, "isolation_rules": a.isolation_rules,
        }, ensure_ascii=False)
        # Increment version
        parts = a.version.split(".")
        major = int(parts[0]); minor = int(parts[1]) if len(parts) > 1 else 0
        new_version = f"{major}.{minor + 1}"
        s.add(Ai2biAgentVersion(
            agent_id=agent_id, version=a.version, snapshot=snapshot,
            changelog=changelog, published_by="admin", published_at=datetime.now(),
        ))
        a.version = new_version
        a.status = "published"
        a.updated_at = datetime.now()
        s.add(a); s.commit()
        return {"status": "published", "version": new_version}

@router.get("/agents/available/{user_id}")
async def available_agents(user_id: int = 1):
    """用户可用的 Agent（含通识兜底）"""
    with _session() as s:
        # Get user's agent grants
        grant_ids = [g.agent_id for g in s.exec(
            select(Ai2biAgentGrant).where(
                Ai2biAgentGrant.user_id == user_id,
                Ai2biAgentGrant.status == "active"
            )).all()]
        # Get published agents
        agents = s.exec(select(Ai2biAgent).where(
            Ai2biAgent.status == "published"
        )).all()
        result = []
        for a in agents:
            result.append({
                "id": a.id, "code": a.code, "name": a.name,
                "vertical": a.vertical,
                "entry_signals": a.entry_signals or [],
                "has_access": a.id in grant_ids or user_id == 1,  # admin has all
            })
        return result

@router.post("/agents/{agent_id}/request")
async def request_access(agent_id: int, user_id: int = 1, reason: str = Body("", embed=True)):
    with _session() as s:
        existing = s.exec(select(Ai2biAgentRequest).where(
            Ai2biAgentRequest.agent_id == agent_id,
            Ai2biAgentRequest.user_id == user_id,
            Ai2biAgentRequest.status == "pending"
        )).first()
        if existing:
            return {"status": "pending_exists"}
        s.add(Ai2biAgentRequest(agent_id=agent_id, user_id=user_id, reason=reason,
                                 created_at=datetime.now()))
        s.commit()
        return {"status": "submitted"}


# ═══ 证据链查询 ═══════════════════════════════════════

@router.get("/evidence/{record_id}")
async def get_evidence(record_id: int):
    """查询某条回答的证据链记录"""
    from apps.ai2bi.evidence_models import Ai2biEvidence
    with _session() as s:
        ev = s.exec(select(Ai2biEvidence).where(Ai2biEvidence.record_id == record_id)).first()
        if not ev:
            return {"found": False}
        import json as _json
        return {
            "found": True,
            "record_id": ev.record_id,
            "chat_id": ev.chat_id,
            "agent_id": ev.agent_id,
            "route_info": _json.loads(ev.route_info) if ev.route_info else None,
            "sql_text": ev.sql_text,
            "sql_executed": ev.sql_executed,
            "sql_row_count": ev.sql_row_count,
            "sql_result_summary": _json.loads(ev.sql_result_summary) if ev.sql_result_summary else None,
            "sourced_numbers": _json.loads(ev.sourced_numbers) if ev.sourced_numbers else [],
            "derived_numbers": _json.loads(ev.derived_numbers) if ev.derived_numbers else [],
            "model_inferred": _json.loads(ev.model_inferred) if ev.model_inferred else [],
            "qa_passed": ev.qa_passed,
            "qa_violations": _json.loads(ev.qa_violations) if ev.qa_violations else [],
            "created_at": str(ev.created_at) if ev.created_at else None,
        }


# ═══ 回归测试 ═══════════════════════════════════════════

@router.post("/agents/{agent_id}/test")
async def run_agent_tests(agent_id: int):
    """运行 Agent 的回归测试集"""
    from apps.ai2bi.test_runner import run_test_cases_for_agent, load_test_cases_from_file

    # 如果 DB 中没有测试用例，尝试从 AIBI_v2 文件加载
    with _session() as s:
        from apps.ai2bi.test_models import Ai2biTestCase
        existing = s.exec(select(Ai2biTestCase).where(Ai2biTestCase.agent_id == agent_id)).all()
        if not existing:
            # 从 AIBI_v2 文件加载
            agent = s.get(Ai2biAgent, agent_id)
            if agent:
                file_cases = load_test_cases_from_file(agent.code)
                for fc in file_cases:
                    tc = Ai2biTestCase(
                        agent_id=agent_id,
                        test_type=fc.get("test_type", "routing"),
                        question=fc.get("question", ""),
                        expected_agent=fc.get("expected_agent"),
                        expected_tables=json.dumps(fc.get("expected_tables", []), ensure_ascii=False),
                        expected_sql_pattern=json.dumps(fc.get("expected_sql_patterns", fc.get("expected_sql_pattern", [])), ensure_ascii=False),
                        expected_evidence_count=fc.get("expected_evidence_count", 0),
                        created_at=datetime.now(),
                    )
                    s.add(tc)
                s.commit()

    result = run_test_cases_for_agent(agent_id)
    return result


@router.get("/agents/{agent_id}/test-results")
async def get_agent_test_results(agent_id: int, limit: int = 10):
    """获取 Agent 的测试运行历史"""
    from apps.ai2bi.test_models import Ai2biTestRun
    with _session() as s:
        runs = s.exec(
            select(Ai2biTestRun)
            .where(Ai2biTestRun.agent_id == agent_id)
            .order_by(Ai2biTestRun.run_at.desc())
            .limit(limit)
        ).all()
        return [{
            "id": r.id, "total": r.total, "passed": r.passed, "failed": r.failed,
            "run_at": str(r.run_at) if r.run_at else None,
        } for r in runs]


def _guess_layer(table_name: str) -> str:
    if table_name.startswith("dwd_"): return "dwd"
    if table_name.startswith("dws_"): return "dws"
    if table_name.startswith("dim_"): return "dim"
    if table_name.startswith("dm_"): return "dm"
    if table_name.startswith("odm_"): return "odm"
    return "other"


# ═════════════════════════════════════════════════════
# 数据资产元数据 API (asset_models)
# ═════════════════════════════════════════════════════

# ── 通用 Pydantic Schemas ──

class TableDictCreate(BaseModel):
    domain_code: str
    table_name: str
    table_comment: Optional[str] = None
    layer: str = "other"
    datasource_id: Optional[int] = None
    field_count: int = 0
    metric_count: int = 0
    dimension_count: int = 0
    upstream_tables: Optional[str] = None
    ddl_content: Optional[str] = None
    is_active: bool = True

class TableDictUpdate(BaseModel):
    domain_code: Optional[str] = None
    table_name: Optional[str] = None
    table_comment: Optional[str] = None
    layer: Optional[str] = None
    datasource_id: Optional[int] = None
    field_count: Optional[int] = None
    metric_count: Optional[int] = None
    dimension_count: Optional[int] = None
    upstream_tables: Optional[str] = None
    ddl_content: Optional[str] = None
    is_active: Optional[bool] = None

class FieldDictCreate(BaseModel):
    table_id: int
    domain_code: str
    field_name: str
    field_type: str
    field_comment: Optional[str] = None
    category: str = "other"
    aggregation: Optional[str] = None
    is_partition: bool = False
    is_primary_key: bool = False
    is_nullable: bool = True
    sample_values: Optional[str] = None

class FieldDictUpdate(BaseModel):
    table_id: Optional[int] = None
    domain_code: Optional[str] = None
    field_name: Optional[str] = None
    field_type: Optional[str] = None
    field_comment: Optional[str] = None
    category: Optional[str] = None
    aggregation: Optional[str] = None
    is_partition: Optional[bool] = None
    is_primary_key: Optional[bool] = None
    is_nullable: Optional[bool] = None
    sample_values: Optional[str] = None

class MetricDictCreate(BaseModel):
    domain_code: str
    cn_name: str
    metric_number: Optional[str] = None
    en_name: Optional[str] = None
    alias: Optional[str] = None
    business_definition: Optional[str] = None
    calculation: Optional[str] = None
    sql_template: Optional[str] = None
    grain: Optional[str] = None
    time_range: Optional[str] = None
    unit: Optional[str] = None
    source_table_id: Optional[int] = None
    source_field: Optional[str] = None
    related_metrics: Optional[str] = None
    status: str = "candidate"
    version: str = "1.0"

class MetricDictUpdate(BaseModel):
    domain_code: Optional[str] = None
    cn_name: Optional[str] = None
    metric_number: Optional[str] = None
    en_name: Optional[str] = None
    alias: Optional[str] = None
    business_definition: Optional[str] = None
    calculation: Optional[str] = None
    sql_template: Optional[str] = None
    grain: Optional[str] = None
    time_range: Optional[str] = None
    unit: Optional[str] = None
    source_table_id: Optional[int] = None
    source_field: Optional[str] = None
    related_metrics: Optional[str] = None
    status: Optional[str] = None
    version: Optional[str] = None

class BusinessRuleCreate(BaseModel):
    domain_code: str
    title: str
    content: str
    category: str = "general"
    related_table_id: Optional[int] = None
    related_metric_id: Optional[int] = None
    severity: str = "warning"
    example: Optional[str] = None
    counter_example: Optional[str] = None

class BusinessRuleUpdate(BaseModel):
    domain_code: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    related_table_id: Optional[int] = None
    related_metric_id: Optional[int] = None
    severity: Optional[str] = None
    example: Optional[str] = None
    counter_example: Optional[str] = None

class SqlTemplateCreate(BaseModel):
    domain_code: str
    name: str
    description: Optional[str] = None
    scenario: Optional[str] = None
    sql_template: str = ""
    params: Optional[str] = None
    related_table_ids: Optional[str] = None
    related_metric_ids: Optional[str] = None

class SqlTemplateUpdate(BaseModel):
    domain_code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    scenario: Optional[str] = None
    sql_template: Optional[str] = None
    params: Optional[str] = None
    related_table_ids: Optional[str] = None
    related_metric_ids: Optional[str] = None

class TableLineageCreate(BaseModel):
    domain_code: str
    from_table: str
    to_table: str
    relation_type: str = "direct"
    sql_snippet: Optional[str] = None


# ── ai2bi_table_dict (表字典) ──

@router.get("/assets/tables")
async def list_tables(domain: str = "", search: str = "", layer: str = "", page: int = 1, size: int = 50):
    """表字典列表"""
    with _session() as s:
        q = select(Ai2biTableDict)
        if domain:
            q = q.where(Ai2biTableDict.domain_code == domain)
        if search:
            q = q.where(Ai2biTableDict.table_name.ilike(f"%{search}%"))
        if layer:
            q = q.where(Ai2biTableDict.layer == layer)
        total = len(s.exec(q).all())
        q = q.order_by(Ai2biTableDict.id.desc()).offset((page - 1) * size).limit(size)
        rows = s.exec(q).all()
        return {
            "total": total,
            "items": [{"id": r.id, "domain_code": r.domain_code, "table_name": r.table_name,
                       "table_comment": r.table_comment, "layer": r.layer,
                       "field_count": r.field_count, "metric_count": r.metric_count,
                       "is_active": r.is_active, "created_at": str(r.created_at) if r.created_at else None} for r in rows]
        }

@router.post("/assets/tables")
async def create_table(body: TableDictCreate):
    """新增表字典记录"""
    with _session() as s:
        t = Ai2biTableDict(**body.dict(), created_at=datetime.now(), updated_at=datetime.now())
        s.add(t); s.commit(); s.refresh(t)
        return {"id": t.id, "status": "created"}

@router.get("/assets/tables/{table_id}")
async def get_table(table_id: int):
    """表字典详情"""
    with _session() as s:
        t = s.get(Ai2biTableDict, table_id)
        if not t: raise HTTPException(404, "Table not found")
        return {"id": t.id, "domain_code": t.domain_code, "table_name": t.table_name,
                "table_comment": t.table_comment, "layer": t.layer,
                "datasource_id": t.datasource_id, "field_count": t.field_count,
                "metric_count": t.metric_count, "dimension_count": t.dimension_count,
                "upstream_tables": t.upstream_tables, "ddl_content": t.ddl_content,
                "is_active": t.is_active, "created_at": str(t.created_at) if t.created_at else None}

@router.put("/assets/tables/{table_id}")
async def update_table(table_id: int, body: TableDictUpdate):
    """更新表字典"""
    with _session() as s:
        t = s.get(Ai2biTableDict, table_id)
        if not t: raise HTTPException(404, "Table not found")
        for k, v in body.dict(exclude_unset=True).items():
            setattr(t, k, v)
        t.updated_at = datetime.now()
        s.add(t); s.commit()
        return {"status": "updated"}

@router.delete("/assets/tables/{table_id}")
async def delete_table(table_id: int):
    """删除表字典（级联删除字段）"""
    with _session() as s:
        t = s.get(Ai2biTableDict, table_id)
        if not t: raise HTTPException(404, "Table not found")
        s.delete(t); s.commit()
        return {"status": "deleted"}


# ── ai2bi_field_dict (字段字典) ──

@router.get("/assets/tables/{table_id}/fields")
async def list_fields(table_id: int):
    """某表的字段列表"""
    with _session() as s:
        fields = s.exec(select(Ai2biFieldDict).where(Ai2biFieldDict.table_id == table_id)).all()
        return [{"id": f.id, "domain_code": f.domain_code, "field_name": f.field_name,
                 "field_type": f.field_type, "field_comment": f.field_comment,
                 "category": f.category, "aggregation": f.aggregation,
                 "is_partition": f.is_partition, "is_primary_key": f.is_primary_key,
                 "is_nullable": f.is_nullable} for f in fields]

@router.get("/assets/fields")
async def list_all_fields(domain: str = "", table_id: int = 0, search: str = "", page: int = 1, size: int = 50):
    """全量字段列表（支持搜索）"""
    with _session() as s:
        q = select(Ai2biFieldDict)
        if domain:
            q = q.where(Ai2biFieldDict.domain_code == domain)
        if table_id:
            q = q.where(Ai2biFieldDict.table_id == table_id)
        if search:
            q = q.where(Ai2biFieldDict.field_name.ilike(f"%{search}%"))
        total = len(s.exec(q).all())
        q = q.order_by(Ai2biFieldDict.id.desc()).offset((page - 1) * size).limit(size)
        rows = s.exec(q).all()
        return {
            "total": total,
            "items": [{"id": f.id, "table_id": f.table_id, "domain_code": f.domain_code,
                       "field_name": f.field_name, "field_type": f.field_type,
                       "field_comment": f.field_comment, "category": f.category,
                       "is_partition": f.is_partition, "is_primary_key": f.is_primary_key} for f in rows]
        }

@router.post("/assets/fields")
async def create_field(body: FieldDictCreate):
    """新增字段"""
    with _session() as s:
        f = Ai2biFieldDict(**body.dict(), created_at=datetime.now())
        s.add(f); s.commit(); s.refresh(f)
        return {"id": f.id, "status": "created"}

@router.put("/assets/fields/{field_id}")
async def update_field(field_id: int, body: FieldDictUpdate):
    """更新字段"""
    with _session() as s:
        f = s.get(Ai2biFieldDict, field_id)
        if not f: raise HTTPException(404, "Field not found")
        for k, v in body.dict(exclude_unset=True).items():
            setattr(f, k, v)
        s.add(f); s.commit()
        return {"status": "updated"}

@router.delete("/assets/fields/{field_id}")
async def delete_field(field_id: int):
    """删除字段"""
    with _session() as s:
        f = s.get(Ai2biFieldDict, field_id)
        if not f: raise HTTPException(404, "Field not found")
        s.delete(f); s.commit()
        return {"status": "deleted"}


# ── ai2bi_metric_dict (核心指标) ──

@router.get("/assets/metrics")
async def list_metrics(domain: str = "", search: str = "", status: str = "", page: int = 1, size: int = 50):
    """核心指标列表"""
    with _session() as s:
        q = select(Ai2biMetricDict)
        if domain:
            q = q.where(Ai2biMetricDict.domain_code == domain)
        if search:
            q = q.where(Ai2biMetricDict.cn_name.ilike(f"%{search}%"))
        if status:
            q = q.where(Ai2biMetricDict.status == status)
        total = len(s.exec(q).all())
        q = q.order_by(Ai2biMetricDict.id.desc()).offset((page - 1) * size).limit(size)
        rows = s.exec(q).all()
        return {
            "total": total,
            "items": [{"id": r.id, "domain_code": r.domain_code, "metric_number": r.metric_number,
                       "cn_name": r.cn_name, "en_name": r.en_name, "alias": r.alias,
                       "business_definition": r.business_definition,
                       "calculation": r.calculation,
                       "sql_template": r.sql_template,
                       "grain": r.grain, "unit": r.unit, "status": r.status,
                       "created_at": str(r.created_at) if r.created_at else None} for r in rows]
        }

@router.get("/assets/metrics/{metric_id}")
async def get_metric(metric_id: int):
    """指标详情"""
    with _session() as s:
        m = s.get(Ai2biMetricDict, metric_id)
        if not m: raise HTTPException(404, "Metric not found")
        return {k: getattr(m, k) for k in m.__fields__.keys()} | {
            "created_at": str(m.created_at) if m.created_at else None,
            "updated_at": str(m.updated_at) if m.updated_at else None,
        }

@router.post("/assets/metrics")
async def create_metric(body: MetricDictCreate):
    """新增指标"""
    with _session() as s:
        m = Ai2biMetricDict(**body.dict(), created_at=datetime.now(), updated_at=datetime.now())
        s.add(m); s.commit(); s.refresh(m)
        return {"id": m.id, "status": "created"}

@router.put("/assets/metrics/{metric_id}")
async def update_metric(metric_id: int, body: MetricDictUpdate):
    """更新指标"""
    with _session() as s:
        m = s.get(Ai2biMetricDict, metric_id)
        if not m: raise HTTPException(404, "Metric not found")
        for k, v in body.dict(exclude_unset=True).items():
            setattr(m, k, v)
        m.updated_at = datetime.now()
        s.add(m); s.commit()
        return {"status": "updated"}

@router.delete("/assets/metrics/{metric_id}")
async def delete_metric(metric_id: int):
    """删除指标"""
    with _session() as s:
        m = s.get(Ai2biMetricDict, metric_id)
        if not m: raise HTTPException(404, "Metric not found")
        s.delete(m); s.commit()
        return {"status": "deleted"}


# ── ai2bi_business_rule (业务规则/注意事项) ──

@router.get("/assets/rules")
async def list_business_rules(domain: str = "", category: str = "", severity: str = "", page: int = 1, size: int = 50):
    """业务规则列表"""
    with _session() as s:
        q = select(Ai2biBusinessRule)
        if domain:
            q = q.where(Ai2biBusinessRule.domain_code == domain)
        if category:
            q = q.where(Ai2biBusinessRule.category == category)
        if severity:
            q = q.where(Ai2biBusinessRule.severity == severity)
        total = len(s.exec(q).all())
        q = q.order_by(Ai2biBusinessRule.id.desc()).offset((page - 1) * size).limit(size)
        rows = s.exec(q).all()
        return {
            "total": total,
            "items": [{"id": r.id, "domain_code": r.domain_code, "title": r.title,
                       "content": r.content,
                       "category": r.category, "severity": r.severity,
                       "created_at": str(r.created_at) if r.created_at else None} for r in rows]
        }

@router.get("/assets/rules/{rule_id}")
async def get_rule(rule_id: int):
    """规则详情"""
    with _session() as s:
        r = s.get(Ai2biBusinessRule, rule_id)
        if not r: raise HTTPException(404, "Rule not found")
        return {"id": r.id, "domain_code": r.domain_code, "title": r.title, "content": r.content,
                "category": r.category, "related_table_id": r.related_table_id,
                "related_metric_id": r.related_metric_id, "severity": r.severity,
                "example": r.example, "counter_example": r.counter_example,
                "created_at": str(r.created_at) if r.created_at else None}

@router.post("/assets/rules")
async def create_rule(body: BusinessRuleCreate):
    """新增规则"""
    with _session() as s:
        r = Ai2biBusinessRule(**body.dict(), created_at=datetime.now(), updated_at=datetime.now())
        s.add(r); s.commit(); s.refresh(r)
        return {"id": r.id, "status": "created"}

@router.put("/assets/rules/{rule_id}")
async def update_rule(rule_id: int, body: BusinessRuleUpdate):
    """更新规则"""
    with _session() as s:
        r = s.get(Ai2biBusinessRule, rule_id)
        if not r: raise HTTPException(404, "Rule not found")
        for k, v in body.dict(exclude_unset=True).items():
            setattr(r, k, v)
        r.updated_at = datetime.now()
        s.add(r); s.commit()
        return {"status": "updated"}

@router.delete("/assets/rules/{rule_id}")
async def delete_rule(rule_id: int):
    """删除规则"""
    with _session() as s:
        r = s.get(Ai2biBusinessRule, rule_id)
        if not r: raise HTTPException(404, "Rule not found")
        s.delete(r); s.commit()
        return {"status": "deleted"}


# ── ai2bi_sql_template (SQL 模板) ──

@router.get("/assets/sql-templates")
async def list_sql_templates(domain: str = "", scenario: str = "", page: int = 1, size: int = 50):
    """SQL 模板列表"""
    with _session() as s:
        q = select(Ai2biSqlTemplate)
        if domain:
            q = q.where(Ai2biSqlTemplate.domain_code == domain)
        if scenario:
            q = q.where(Ai2biSqlTemplate.scenario == scenario)
        total = len(s.exec(q).all())
        q = q.order_by(Ai2biSqlTemplate.id.desc()).offset((page - 1) * size).limit(size)
        rows = s.exec(q).all()
        return {
            "total": total,
            "items": [{"id": r.id, "domain_code": r.domain_code, "name": r.name,
                       "scenario": r.scenario, "usage_count": r.usage_count,
                       "created_at": str(r.created_at) if r.created_at else None} for r in rows]
        }

@router.get("/assets/sql-templates/{tpl_id}")
async def get_sql_template(tpl_id: int):
    """SQL 模板详情"""
    with _session() as s:
        t = s.get(Ai2biSqlTemplate, tpl_id)
        if not t: raise HTTPException(404, "Template not found")
        return {"id": t.id, "domain_code": t.domain_code, "name": t.name,
                "description": t.description, "scenario": t.scenario,
                "sql_template": t.sql_template, "params": t.params,
                "related_table_ids": t.related_table_ids,
                "related_metric_ids": t.related_metric_ids,
                "usage_count": t.usage_count}

@router.post("/assets/sql-templates")
async def create_sql_template(body: SqlTemplateCreate):
    """新增 SQL 模板"""
    with _session() as s:
        t = Ai2biSqlTemplate(**body.dict(), created_at=datetime.now(), updated_at=datetime.now())
        s.add(t); s.commit(); s.refresh(t)
        return {"id": t.id, "status": "created"}

@router.put("/assets/sql-templates/{tpl_id}")
async def update_sql_template(tpl_id: int, body: SqlTemplateUpdate):
    """更新 SQL 模板"""
    with _session() as s:
        t = s.get(Ai2biSqlTemplate, tpl_id)
        if not t: raise HTTPException(404, "Template not found")
        for k, v in body.dict(exclude_unset=True).items():
            setattr(t, k, v)
        t.updated_at = datetime.now()
        s.add(t); s.commit()
        return {"status": "updated"}

@router.delete("/assets/sql-templates/{tpl_id}")
async def delete_sql_template(tpl_id: int):
    """删除 SQL 模板"""
    with _session() as s:
        t = s.get(Ai2biSqlTemplate, tpl_id)
        if not t: raise HTTPException(404, "Template not found")
        s.delete(t); s.commit()
        return {"status": "deleted"}


# ── ai2bi_table_lineage (表血缘) ──

@router.get("/assets/lineage")
async def list_lineage(domain: str = "", from_table: str = "", to_table: str = "", page: int = 1, size: int = 50):
    """血缘关系列表"""
    with _session() as s:
        q = select(Ai2biTableLineage)
        if domain:
            q = q.where(Ai2biTableLineage.domain_code == domain)
        if from_table:
            q = q.where(Ai2biTableLineage.from_table == from_table)
        if to_table:
            q = q.where(Ai2biTableLineage.to_table == to_table)
        total = len(s.exec(q).all())
        q = q.order_by(Ai2biTableLineage.id.desc()).offset((page - 1) * size).limit(size)
        rows = s.exec(q).all()
        return {
            "total": total,
            "items": [{"id": r.id, "domain_code": r.domain_code, "from_table": r.from_table,
                       "to_table": r.to_table, "relation_type": r.relation_type,
                       "sql_snippet": r.sql_snippet,
                       "created_at": str(r.created_at) if r.created_at else None} for r in rows]
        }

@router.post("/assets/lineage")
async def create_lineage(body: TableLineageCreate):
    """新增血缘关系"""
    with _session() as s:
        l = Ai2biTableLineage(**body.dict(), created_at=datetime.now())
        s.add(l); s.commit(); s.refresh(l)
        return {"id": l.id, "status": "created"}

@router.delete("/assets/lineage/{lineage_id}")
async def delete_lineage(lineage_id: int):
    """删除血缘关系"""
    with _session() as s:
        l = s.get(Ai2biTableLineage, lineage_id)
        if not l: raise HTTPException(404, "Lineage not found")
        s.delete(l); s.commit()
        return {"status": "deleted"}


# ── Agent 上下文接口：路由命中时加载域元数据 ──

@router.get("/assets/domain-context/{domain_code}")
async def get_domain_context(domain_code: str):
    """获取某个业务域的完整上下文（Agent 用）
    
    返回该域的表字典、字段字典、指标、规则，供 Agent 路由命中时注入上下文。
    """
    with _session() as s:
        # Tables
        tables = s.exec(
            select(Ai2biTableDict).where(Ai2biTableDict.domain_code == domain_code)
        ).all()
        table_ids = [t.id for t in tables]
        
        # Fields
        fields = s.exec(
            select(Ai2biFieldDict).where(Ai2biFieldDict.table_id.in_(table_ids))
        ).all() if table_ids else []
        
        # Metrics
        metrics = s.exec(
            select(Ai2biMetricDict).where(Ai2biMetricDict.domain_code == domain_code)
        ).all()
        
        # Rules
        rules = s.exec(
            select(Ai2biBusinessRule).where(Ai2biBusinessRule.domain_code == domain_code)
        ).all()
        
        # SQL Templates
        templates = s.exec(
            select(Ai2biSqlTemplate).where(Ai2biSqlTemplate.domain_code == domain_code)
        ).all()
        
        return {
            "domain_code": domain_code,
            "tables": [{"id": t.id, "table_name": t.table_name, "table_comment": t.table_comment,
                        "layer": t.layer, "field_count": t.field_count} for t in tables],
            "fields": [{"id": f.id, "table_id": f.table_id, "field_name": f.field_name,
                        "field_type": f.field_type, "field_comment": f.field_comment,
                        "category": f.category} for f in fields],
            "metrics": [{"id": m.id, "metric_number": m.metric_number, "cn_name": m.cn_name,
                         "calculation": m.calculation, "grain": m.grain} for m in metrics],
            "rules": [{"id": r.id, "title": r.title, "content": r.content,
                       "category": r.category, "severity": r.severity} for r in rules],
            "sql_templates": [{"id": t.id, "name": t.name, "scenario": t.scenario,
                               "sql_template": t.sql_template} for t in templates],
        }


# ── 批量导入接口（从知识库同步） ──

@router.post("/assets/sync-tables")
async def sync_tables_from_source(tables: list[dict] = Body(..., embed=False)):
    """批量导入表字典（从 DDL 解析结果同步）
    
    请求体: [{"domain_code", "table_name", "table_comment", "layer", "ddl_content", "fields": [...]}]
    """
    import json as _json
    with _session() as s:
        for item in tables:
            # Upsert table
            existing = s.exec(
                select(Ai2biTableDict).where(
                    Ai2biTableDict.domain_code == item.get("domain_code"),
                    Ai2biTableDict.table_name == item.get("table_name")
                )
            ).first()
            if existing:
                t = existing
                t.table_comment = item.get("table_comment", t.table_comment)
                t.layer = item.get("layer", t.layer)
                t.ddl_content = item.get("ddl_content", t.ddl_content)
                t.updated_at = datetime.now()
            else:
                t = Ai2biTableDict(
                    domain_code=item.get("domain_code"),
                    table_name=item.get("table_name"),
                    table_comment=item.get("table_comment"),
                    layer=item.get("layer", "other"),
                    ddl_content=item.get("ddl_content"),
                    field_count=len(item.get("fields", [])),
                    created_at=datetime.now(), updated_at=datetime.now(),
                )
                s.add(t); s.commit(); s.refresh(t)
            
            # Sync fields
            for f in item.get("fields", []):
                fe = s.exec(
                    select(Ai2biFieldDict).where(
                        Ai2biFieldDict.table_id == t.id,
                        Ai2biFieldDict.field_name == f.get("field_name")
                    )
                ).first()
                if not fe:
                    s.add(Ai2biFieldDict(
                        table_id=t.id,
                        domain_code=item.get("domain_code"),
                        field_name=f.get("field_name"),
                        field_type=f.get("field_type", "STRING"),
                        field_comment=f.get("field_comment"),
                        category=f.get("category", "other"),
                        is_partition=f.get("is_partition", False),
                        created_at=datetime.now(),
                    ))
        s.commit()
        return {"status": "synced", "tables_count": len(tables)}
